from fastapi import FastAPI, BackgroundTasks, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from typing import List, Optional
import uvicorn
from pydantic import BaseModel
import os
import json
from dotenv import load_dotenv
from datetime import datetime
import asyncio
import logging
import concurrent.futures
import time

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')

# Import scrapers
from scrapers.flatfox_scraper import FlatfoxScraper
from scrapers.homegate_scraper import HomegateScraper
from scrapers.immoscout_scraper import ImmoscoutScraper
from matcher import PropertyMatcher

# Load environment variables
load_dotenv()

app = FastAPI(title="Swiss Apartment Matcher")

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class SearchCriteria(BaseModel):
    location: str
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    min_rooms: Optional[float] = None
    max_rooms: Optional[float] = None
    min_size: Optional[float] = None
    max_size: Optional[float] = None
    features: Optional[List[str]] = None

class PropertyListing(BaseModel):
    title: str
    price: float
    location: str
    rooms: Optional[float] = None
    size: Optional[float] = None
    features: Optional[List[str]] = None
    link: str
    source: str
    created_at: datetime = datetime.now()

class MatchResult(BaseModel):
    listing: PropertyListing
    match_score: float
    matching_criteria: List[str]
    missing_criteria: List[str]

# Scraper pool
scraper_pool = {
    'flatfox': FlatfoxScraper(),
    'homegate': HomegateScraper(),
    'immoscout': ImmoscoutScraper()
}

# Initialize matcher
matcher = PropertyMatcher()

async def scrape_website(scraper_name: str, scraper, search_criteria: dict) -> List[dict]:
    """
    Scrape a website asynchronously
    """
    start_time = time.time()
    logger = logging.getLogger(scraper_name)
    
    try:
        logger.info(f"Starting scraping {scraper_name}")
        loop = asyncio.get_running_loop()
        
        with concurrent.futures.ThreadPoolExecutor() as pool:
            listings = await loop.run_in_executor(
                pool, 
                scraper.scrape,
                search_criteria
            )
            
        duration = time.time() - start_time
        logger.info(f"Finished scraping {scraper_name}. Found {len(listings)} listings in {duration:.2f} seconds")
        return listings
        
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Error scraping {scraper_name} after {duration:.2f} seconds: {str(e)}")
        return []

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Render the main page"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/search", response_model=List[MatchResult])
async def search_apartments(criteria: SearchCriteria, background_tasks: BackgroundTasks):
    """
    Search for apartments matching the given criteria across multiple websites
    """
    logger = logging.getLogger("search")
    start_time = time.time()
    logger.info(f"Starting search with criteria: {json.dumps(criteria.dict())}")
    
    # Create list of scraping tasks
    scraping_tasks = [
        scrape_website(name, scraper, criteria.dict())
        for name, scraper in scraper_pool.items()
    ]
    
    # Run scrapers concurrently
    try:
        results = await asyncio.gather(*scraping_tasks)
    except Exception as e:
        logger.error(f"Error during concurrent scraping: {str(e)}")
        results = []
    
    # Combine all listings
    all_listings = []
    for listings in results:
        if listings:
            all_listings.extend(listings)
            
    logger.info(f"Found {len(all_listings)} total listings before matching")
    
    # Match listings against criteria
    matches = matcher.match_listings(criteria, all_listings)
    
    # Sort by match score
    matches.sort(key=lambda x: x.match_score, reverse=True)
    
    duration = time.time() - start_time
    logger.info(f"Search completed in {duration:.2f} seconds. Found {len(matches)} matching listings")
    
    # Cleanup scrapers
    background_tasks.add_task(cleanup_scrapers)
    
    if not matches:
        return JSONResponse(
            content={
                "message": "No matching listings found",
                "search_criteria": criteria.dict(),
                "total_listings_scraped": len(all_listings),
                "duration_seconds": duration
            },
            status_code=404
        )
    
    return matches

@app.get("/healthcheck")
async def healthcheck():
    """
    Check if the service is running
    """
    try:
        # Try to initialize a test scraper
        test_scraper = FlatfoxScraper()
        test_scraper.cleanup()
        return {"status": "healthy", "message": "Service is running normally"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"status": "unhealthy", "message": str(e)}
        )

def cleanup_scrapers():
    """Cleanup all scrapers"""
    for name, scraper in scraper_pool.items():
        try:
            logger = logging.getLogger(name)
            logger.info("Cleaning up scraper resources")
            scraper.cleanup()
        except Exception as e:
            logger.error(f"Error during scraper cleanup: {str(e)}")

if __name__ == "__main__":
    try:
        uvicorn.run(app, host="0.0.0.0", port=8000)
    finally:
        cleanup_scrapers()
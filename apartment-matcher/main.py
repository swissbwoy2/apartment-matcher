from fastapi import FastAPI, BackgroundTasks, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from models import SearchCriteria, MatchResult, PropertyListing
from scrapers.flatfox_scraper import FlatfoxScraper
from scrapers.homegate_scraper import HomegateScraper
from scrapers.immoscout_scraper import ImmoscoutScraper
from matcher import PropertyMatcher
from database import Database
from email_notifier import EmailNotifier
from typing import List, Optional
import uvicorn
from pydantic import BaseModel
import os
from dotenv import load_dotenv

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

# Initialize components
db = Database()
matcher = PropertyMatcher()
notifier = EmailNotifier()
scrapers = {
    'flatfox': FlatfoxScraper(),
    'homegate': HomegateScraper(),
    'immoscout': ImmoscoutScraper()
}

class SearchProfileCreate(BaseModel):
    email: str
    criteria: SearchCriteria
    notification_frequency: str = "daily"

@app.get("/")
async def read_root(request: Request):
    """Render the main page"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/search", response_model=List[MatchResult])
async def search_apartments(criteria: SearchCriteria, background_tasks: BackgroundTasks):
    """
    Search for apartments matching the given criteria across multiple websites
    """
    all_listings = []
    
    try:
        # Run scrapers
        for scraper_name, scraper in scrapers.items():
            try:
                listings = scraper.scrape(criteria.dict())
                all_listings.extend(listings)
                
                # Save listings to database
                for listing in listings:
                    db.add_listing(listing)
                    
            except Exception as e:
                print(f"Error with {scraper_name}: {e}")
    finally:
        # Cleanup scrapers
        background_tasks.add_task(lambda: [scraper.cleanup() for scraper in scrapers.values()])
    
    # Match listings against criteria
    matches = matcher.match_listings(criteria, all_listings)
    
    # Sort by match score
    matches.sort(key=lambda x: x.match_score, reverse=True)
    
    return matches

@app.post("/profiles", status_code=201)
async def create_search_profile(profile: SearchProfileCreate):
    """
    Create a new search profile for email notifications
    """
    try:
        db.add_search_profile(
            email=profile.email,
            criteria=profile.criteria.dict(),
            frequency=profile.notification_frequency
        )
        return {"message": "Search profile created successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/profiles/{email}", response_model=List[dict])
async def get_search_profiles(email: str):
    """
    Get all search profiles for a given email
    """
    profiles = db.get_search_profiles()
    return [
        {
            "email": p.user_email,
            "criteria": p.criteria,
            "frequency": p.notification_frequency,
            "last_notification": p.last_notification
        }
        for p in profiles if p.user_email == email
    ]

@app.delete("/profiles/{profile_id}")
async def delete_search_profile(profile_id: int):
    """
    Delete a search profile
    """
    try:
        db.delete_profile(profile_id)
        return {"message": "Profile deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.get("/healthcheck")
async def healthcheck():
    """
    Check if the service is running
    """
    return {"status": "healthy"}

@app.on_event("shutdown")
def shutdown_event():
    """Cleanup resources on shutdown"""
    for scraper in scrapers.values():
        scraper.cleanup()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
from typing import Dict, List
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from datetime import datetime
import time
import re
from .base_scraper import BaseScraper

class FlatfoxScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.base_url = "https://flatfox.ch/fr/search/"

    def scrape(self, search_criteria: Dict) -> List[Dict]:
        """
        Scrape Flatfox listings based on search criteria
        """
        listings = []
        
        try:
            url = self._build_search_url(search_criteria)
            print(f"Scraping Flatfox with URL: {url}")
            
            if not self._safe_get(url, ".ListingItem"):
                print("Failed to navigate to Flatfox search page")
                return []
            
            # Wait for listings to load and become interactive
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_all_elements_located((By.CLASS_NAME, "ListingItem"))
                )
            except TimeoutException:
                print("No listings found on page")
                return []
            
            # Let the page fully load
            time.sleep(2)
            
            # Get all listing items
            listing_items = self.driver.find_elements(By.CLASS_NAME, "ListingItem")
            print(f"Found {len(listing_items)} listings")
            
            for item in listing_items:
                try:
                    listing = self._parse_listing(item)
                    if listing and self._matches_criteria(listing, search_criteria):
                        listings.append(listing)
                except Exception as e:
                    print(f"Error parsing listing: {e}")
                    continue
                    
        except Exception as e:
            print(f"Error scraping Flatfox: {e}")
            
        finally:
            print(f"Scraped {len(listings)} matching listings from Flatfox")
            
        return listings

    def _parse_listing(self, item) -> Dict:
        """Parse a listing element and extract relevant information"""
        try:
            # Get basic info
            title = item.find_element(By.CSS_SELECTOR, "h3").text.strip()
            link = item.find_element(By.CSS_SELECTOR, "a").get_attribute("href")
            
            # Get price
            try:
                price_elem = item.find_element(By.CSS_SELECTOR, "[data-cy='price']")
                price_text = price_elem.text.strip()
                price = float(re.sub(r'[^\d.]', '', price_text))
            except (NoSuchElementException, ValueError):
                print(f"Could not parse price for listing: {title}")
                return None
            
            # Get location
            try:
                location = item.find_element(By.CSS_SELECTOR, "[data-cy='address']").text.strip()
            except NoSuchElementException:
                print(f"Could not find location for listing: {title}")
                return None
            
            # Get rooms and size
            details = item.find_element(By.CSS_SELECTOR, "[data-cy='listing-characteristics']").text
            
            rooms = None
            size = None
            
            # Extract rooms
            rooms_match = re.search(r'(\d+(\.\d+)?)\s*pièces?', details)
            if rooms_match:
                rooms = float(rooms_match.group(1))
                
            # Extract size
            size_match = re.search(r'(\d+(\.\d+)?)\s*m²', details)
            if size_match:
                size = float(size_match.group(1))
            
            # Extract features
            features = []
            feature_elements = item.find_elements(By.CSS_SELECTOR, "[data-cy='listing-characteristics'] span")
            
            feature_mapping = {
                'balcon': 'balcony',
                'ascenseur': 'elevator',
                'parking': 'parking',
                'garage': 'parking',
                'terrasse': 'terrace',
                'jardin': 'garden',
                'meublé': 'furnished'
            }
            
            for elem in feature_elements:
                feature_text = elem.text.lower()
                for fr, en in feature_mapping.items():
                    if fr in feature_text:
                        features.append(en)
                        break
            
            return {
                "title": title,
                "price": price,
                "location": location,
                "rooms": rooms,
                "size": size,
                "features": features,
                "link": link,
                "source": "Flatfox",
                "created_at": datetime.now()
            }
            
        except Exception as e:
            print(f"Error parsing listing details: {e}")
            return None

    def _matches_criteria(self, listing: Dict, criteria: Dict) -> bool:
        """Check if a listing matches the search criteria"""
        # Price check
        if criteria.get('min_price') and listing['price'] < criteria['min_price']:
            return False
        if criteria.get('max_price') and listing['price'] > criteria['max_price']:
            return False
            
        # Rooms check
        if criteria.get('min_rooms') and listing['rooms'] and listing['rooms'] < criteria['min_rooms']:
            return False
        if criteria.get('max_rooms') and listing['rooms'] and listing['rooms'] > criteria['max_rooms']:
            return False
            
        # Size check
        if criteria.get('min_size') and listing['size'] and listing['size'] < criteria['min_size']:
            return False
        if criteria.get('max_size') and listing['size'] and listing['size'] > criteria['max_size']:
            return False
            
        # Location check
        if criteria.get('location'):
            location_terms = criteria['location'].lower().split()
            listing_location = listing['location'].lower()
            if not all(term in listing_location for term in location_terms):
                return False
                
        # Features check
        if criteria.get('features'):
            listing_features = set(listing.get('features', []))
            required_features = set(criteria['features'])
            if not required_features.issubset(listing_features):
                return False
                
        return True

    def _build_search_url(self, criteria: Dict) -> str:
        """Build search URL with parameters"""
        url = self.base_url
        
        params = []
        
        if 'location' in criteria:
            params.append(f"q={criteria['location']}")
            
        if 'min_price' in criteria:
            params.append(f"min_price={criteria['min_price']}")
            
        if 'max_price' in criteria:
            params.append(f"max_price={criteria['max_price']}")
            
        if 'min_rooms' in criteria:
            params.append(f"min_rooms={criteria['min_rooms']}")
            
        if 'max_rooms' in criteria:
            params.append(f"max_rooms={criteria['max_rooms']}")
            
        if params:
            url += "?" + "&".join(params)
            
        return url
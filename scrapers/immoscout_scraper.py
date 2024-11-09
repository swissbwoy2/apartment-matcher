from typing import Dict, List
from .base_scraper import BaseScraper
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
import time
import re

class ImmoscoutScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.immoscout24.ch/fr/immobilier/louer/ville-region"

    def scrape(self, search_criteria: Dict) -> List[Dict]:
        """
        Scrape ImmoScout24 listings based on search criteria
        """
        listings = []
        
        try:
            url = self._build_search_url(search_criteria)
            self.driver.get(url)
            
            # Wait for listings to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "PropertyCard"))
            )
            
            # Let the page fully load
            time.sleep(2)
            
            # Get all listing items
            listing_items = self.driver.find_elements(By.CLASS_NAME, "PropertyCard")
            
            for item in listing_items:
                try:
                    listing = self._parse_listing(item)
                    
                    # Apply filters
                    if self._matches_criteria(listing, search_criteria):
                        listings.append(listing)
                except Exception as e:
                    print(f"Error parsing listing: {e}")
                    continue
                    
        except Exception as e:
            print(f"Error scraping ImmoScout24: {e}")
            
        return listings

    def _parse_listing(self, item) -> Dict:
        """
        Parse a listing element and extract relevant information
        """
        try:
            # Get basic info
            title = item.find_element(By.CSS_SELECTOR, ".PropertyCard__title").text.strip()
            link = item.find_element(By.CSS_SELECTOR, "a").get_attribute("href")
            
            # Get price
            price_elem = item.find_element(By.CSS_SELECTOR, ".PropertyCard__price")
            price_text = price_elem.text.strip()
            price = float(re.sub(r'[^\d.]', '', price_text))
            
            # Get location
            location = item.find_element(By.CSS_SELECTOR, ".PropertyCard__location").text.strip()
            
            # Get rooms and size
            details = item.find_element(By.CSS_SELECTOR, ".PropertyCard__details").text
            
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
            feature_elements = item.find_elements(By.CSS_SELECTOR, ".PropertyCard__features span")
            
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
                "source": "ImmoScout24",
                "created_at": datetime.now()
            }
            
        except Exception as e:
            raise Exception(f"Error parsing listing details: {e}")

    def _matches_criteria(self, listing: Dict, criteria: Dict) -> bool:
        """
        Check if a listing matches the search criteria
        """
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
        """
        Build search URL with parameters
        """
        url = self.base_url
        
        # Add location
        if criteria.get('location'):
            url = url.replace('ville-region', criteria['location'].lower().replace(' ', '-'))
        
        params = []
        
        if 'min_price' in criteria:
            params.append(f"pf={criteria['min_price']}")
            
        if 'max_price' in criteria:
            params.append(f"pt={criteria['max_price']}")
            
        if 'min_rooms' in criteria:
            params.append(f"r={criteria['min_rooms']}")
            
        if 'max_rooms' in criteria:
            params.append(f"r={criteria['max_rooms']}")
            
        if params:
            url += "?" + "&".join(params)
            
        return url
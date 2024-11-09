import schedule
import time
from datetime import datetime, timedelta
from database import Database
from matcher import PropertyMatcher
from email_notifier import EmailNotifier
from scrapers.flatfox_scraper import FlatfoxScraper
from scrapers.homegate_scraper import HomegateScraper
from scrapers.immoscout_scraper import ImmoscoutScraper
import json
import threading

class MatchingScheduler:
    def __init__(self):
        self.db = Database()
        self.matcher = PropertyMatcher()
        self.notifier = EmailNotifier()
        self.scrapers = {
            'flatfox': FlatfoxScraper(),
            'homegate': HomegateScraper(),
            'immoscout': ImmoscoutScraper()
        }

    def run_matching(self, frequency: str):
        """Run matching for profiles with given notification frequency"""
        profiles = self.db.get_search_profiles(frequency)
        
        for profile in profiles:
            # Skip if notification was sent too recently
            if profile.last_notification:
                if frequency == 'hourly' and datetime.now() - profile.last_notification < timedelta(hours=1):
                    continue
                elif frequency == 'daily' and datetime.now() - profile.last_notification < timedelta(days=1):
                    continue
            
            # Get new listings since last notification
            new_listings = self.db.get_new_listings(
                profile.last_notification or datetime.now() - timedelta(days=7)
            )
            
            # Match listings against criteria
            criteria = json.loads(profile.criteria)
            matches = self.matcher.match_listings(criteria, new_listings)
            
            # Filter matches with score above threshold (e.g., 70%)
            good_matches = [match for match in matches if match.match_score >= 70]
            
            if good_matches:
                # Send email notification
                self.notifier.send_matches_notification(profile.user_email, good_matches)
                # Update notification time
                self.db.update_notification_time(profile.id)

    def scrape_listings(self):
        """Scrape new listings from all sources"""
        for scraper_name, scraper in self.scrapers.items():
            try:
                # Use empty criteria to get all listings
                listings = scraper.scrape({})
                
                # Save to database
                for listing in listings:
                    self.db.add_listing(listing)
                    
            except Exception as e:
                print(f"Error scraping {scraper_name}: {e}")
            finally:
                scraper.cleanup()

    def start(self):
        """Start the scheduling system"""
        # Schedule scraping every 30 minutes
        schedule.every(30).minutes.do(self.scrape_listings)
        
        # Schedule matching
        schedule.every().hour.at(":00").do(lambda: self.run_matching('hourly'))
        schedule.every().day.at("09:00").do(lambda: self.run_matching('daily'))
        
        # Run initial scraping
        self.scrape_listings()
        
        # Start the scheduler
        while True:
            schedule.run_pending()
            time.sleep(60)

def run_scheduler():
    scheduler = MatchingScheduler()
    scheduler.start()

if __name__ == "__main__":
    # Run scheduler in a separate thread
    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.start()
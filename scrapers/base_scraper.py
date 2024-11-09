from abc import ABC, abstractmethod
from typing import Dict, List
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os

class BaseScraper(ABC):
    def __init__(self):
        self.driver = None
        self.max_retries = 3
        self.retry_delay = 2
        self.page_load_timeout = 30
        self._initialize_driver()
        
    def _initialize_driver(self):
        """Initialize the Chrome WebDriver with appropriate options"""
        try:
            # Configure Chrome options
            chrome_options = Options()
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-notifications")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-infobars")
            chrome_options.add_argument("--disable-popup-blocking")
            chrome_options.add_argument("--ignore-certificate-errors")
            
            # Add performance logging preferences
            chrome_options.set_capability(
                "goog:loggingPrefs",
                {"performance": "ALL", "browser": "ALL"}
            )
            
            # Set Chrome binary location
            chrome_binary = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
            if os.path.exists(chrome_binary):
                chrome_options.binary_location = chrome_binary
            
            # Create Service with specific chromedriver path
            chromedriver_path = "/opt/homebrew/bin/chromedriver"
            if not os.path.exists(chromedriver_path):
                raise Exception(f"ChromeDriver not found at {chromedriver_path}")
            
            service = Service(executable_path=chromedriver_path)
            
            # Initialize Chrome WebDriver with the configured options
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.set_page_load_timeout(self.page_load_timeout)
            self.driver.implicitly_wait(10)
            
            print("WebDriver initialized successfully")
                
        except Exception as e:
            print(f"Error initializing WebDriver: {e}")
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
                self.driver = None
            raise
        
    def _safe_get(self, url: str, wait_selector: str = None) -> bool:
        """
        Safely navigate to a URL with retries and explicit waits
        
        Args:
            url: The URL to navigate to
            wait_selector: CSS selector to wait for after page load
            
        Returns:
            bool: True if navigation was successful, False otherwise
        """
        retry_count = 0
        while retry_count < self.max_retries:
            try:
                # Clear existing alerts if any
                try:
                    alert = self.driver.switch_to.alert
                    alert.accept()
                except:
                    pass
                
                # Navigate to URL
                print(f"Navigating to {url}")
                self.driver.get(url)
                
                # Wait for specific element if selector provided
                if wait_selector:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located(("css selector", wait_selector))
                    )
                    
                return True
                
            except TimeoutException:
                print(f"Timeout loading {url}")
                retry_count += 1
                if retry_count < self.max_retries:
                    print(f"Retrying ({retry_count + 1}/{self.max_retries})...")
                    time.sleep(self.retry_delay)
                    continue
                return False
                
            except WebDriverException as e:
                print(f"Error navigating to {url}: {e}")
                retry_count += 1
                if retry_count < self.max_retries:
                    print(f"Retrying ({retry_count + 1}/{self.max_retries})...")
                    time.sleep(self.retry_delay)
                    continue
                return False
                
            except Exception as e:
                print(f"Unexpected error navigating to {url}: {e}")
                return False
                
        return False
        
    @abstractmethod
    def scrape(self, search_criteria: Dict) -> List[Dict]:
        """
        Abstract method to be implemented by each website scraper
        
        Args:
            search_criteria: Dictionary containing search parameters
            
        Returns:
            List of dictionaries containing property listings
        """
        pass

    def cleanup(self):
        """Close the browser session"""
        try:
            if self.driver:
                print("Cleaning up WebDriver resources")
                self.driver.quit()
        except Exception as e:
            print(f"Error during cleanup: {e}")
        finally:
            self.driver = None
            
    def __del__(self):
        """Ensure driver is closed when object is destroyed"""
        self.cleanup()
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from app.extensions import db
from app.models.service_center import ServiceCenter
import logging
import time
from app.config import Config
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ServiceCenterCrawler:
    def __init__(self):
        self.options = Options()
        self.options.add_argument("--headless")
        self.options.add_argument("--no-sandbox")
        self.options.add_argument("--disable-dev-shm-usage")
        self.options.add_argument("--disable-gpu")
        self.options.add_argument("--disable-software-rasterizer")
        self.api_key = Config.GOOGLE_MAPS_API_KEY
        
    def setup_driver(self):
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=self.options)

    def find_service_centers(self, brand, pincode):
        """Find service centers for a given brand near a pincode"""
        driver = None
        try:
            if not brand or not pincode:
                logger.error("Brand or pincode missing")
                return []

            service_centers = []
            driver = self.setup_driver()
            
            # Search queries to try
            search_queries = [
                f"{brand} authorized service center near {pincode}",
                f"{brand} service center {pincode}"
            ]
            
            for query in search_queries:
                try:
                    # Google Maps search URL
                    search_url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"
                    driver.get(search_url)
                    time.sleep(5)  # Wait for initial load
                    
                    # Updated selectors for modern Google Maps
                    selectors = [
                        "div[role='article']",  # Modern listing container
                        ".section-result",       # Legacy selector
                        ".place-result"          # Alternative selector
                    ]
                    
                    # Try different selectors
                    results = None
                    for selector in selectors:
                        try:
                            wait = WebDriverWait(driver, 10)
                            results = wait.until(EC.presence_of_all_elements_located(
                                (By.CSS_SELECTOR, selector)
                            ))
                            if results:
                                break
                        except:
                            continue
                    
                    if not results:
                        continue
                    
                    for result in results[:5]:
                        try:
                            # Try different name selectors
                            name_selectors = ["h3", ".section-result-title", "[role='heading']"]
                            name = None
                            for selector in name_selectors:
                                try:
                                    name = result.find_element(By.CSS_SELECTOR, selector).text
                                    if name:
                                        break
                                except:
                                    continue
                            
                            # Try different address selectors
                            address_selectors = [
                                ".section-result-location",
                                "[role='link'] > div:nth-child(2)",
                                "div[role='button'] span"
                            ]
                            address = None
                            for selector in address_selectors:
                                try:
                                    address = result.find_element(By.CSS_SELECTOR, selector).text
                                    if address:
                                        break
                                except:
                                    continue
                            
                            if name and address:
                                service_center = {
                                    'name': name,
                                    'address': address,
                                    'brand': brand,
                                    'pincode': pincode,
                                    'latitude': 0.0,
                                    'longitude': 0.0
                                }
                                
                                service_centers.append(service_center)
                                self.save_to_database(service_center)
                        
                        except Exception as e:
                            logger.error(f"Error processing result: {str(e)}")
                            continue
                    
                    if service_centers:
                        break
                        
                except TimeoutException:
                    logger.error(f"Timeout waiting for results for query: {query}")
                    continue
                    
            return service_centers
            
        except Exception as e:
            logger.error(f"Error in find_service_centers: {str(e)}")
            return []
            
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass

    def extract_coordinates(self, maps_url):
        """Extract coordinates from Google Maps URL"""
        try:
            # Example URL format: https://www.google.com/maps?q=12.9716,77.5946
            coords = maps_url.split('@')[1].split(',')[:2]
            return {
                'lat': float(coords[0]),
                'lng': float(coords[1])
            }
        except:
            return {'lat': 0, 'lng': 0}

    def save_to_database(self, service_center):
        """Save service center information to database"""
        try:
            if not all([service_center.get('name'), service_center.get('address'), 
                       service_center.get('brand'), service_center.get('pincode')]):
                logger.error("Missing required fields in service center data")
                return False

            existing = ServiceCenter.query.filter_by(
                name=service_center['name'],
                address=service_center['address'],
                brand=service_center['brand']
            ).first()
            
            if not existing:
                new_center = ServiceCenter(
                    name=service_center['name'],
                    address=service_center['address'],
                    brand=service_center['brand'],
                    pincode=service_center['pincode'],
                    latitude=service_center.get('latitude', 0.0),
                    longitude=service_center.get('longitude', 0.0)
                )
                db.session.add(new_center)
                db.session.commit()
                logger.info(f"Saved service center: {service_center['name']}")
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error saving to database: {str(e)}")
            db.session.rollback()
            return False 
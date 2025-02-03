import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager


def setup_logging():
    os.makedirs("logs", exist_ok=True)

    # Generate a unique log filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"logs/tunisianet_scraper_{timestamp}.log"

    # Configure logging to write to both file and console
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            # Log to file
            logging.FileHandler(log_filename, encoding="utf-8"),
            # Log to console
            logging.StreamHandler(),
        ],
    )

    return log_filename


class TunisiaNetScraper:
    def __init__(
        self, base_url: str = "https://www.tunisianet.com.tn/702-ordinateur-portable"
    ):
        """
        Initialize the web scraper with Chrome WebDriver

        Args:
            base_url (str): Base URL for the product category to scrape
        """
        # Set up logging
        self.logger = logging.getLogger(__name__)
        self.log_file = setup_logging()
        self.logger.info(f"Logging to file: {self.log_file}")

        # Configure Chrome options
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run in background
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        # Set up WebDriver with automatic driver management
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)

        self.base_url = base_url

    def _find_elements(self, by: By, value: str) -> List:
        """
        Wrapper method to find elements with explicit wait

        Args:
            by (By): Selenium By locator
            value (str): Locator value

        Returns:
            List of found WebElements
        """
        try:
            return WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((by, value))
            )
        except Exception as e:
            self.logger.error(f"Error finding elements: {e}")
            return []

    def _extract_text(self, elements: List, filter_empty: bool = True) -> List[str]:
        """
        Extract text from WebElements

        Args:
            elements (List): List of WebElements
            filter_empty (bool): Remove empty strings

        Returns:
            List of extracted text
        """
        texts = [elem.text.strip() for elem in elements]
        return [text for text in texts if text] if filter_empty else texts

    def _extract_attribute(self, elements: List, attribute: str) -> List[str]:
        """
        Extract specific attribute from WebElements

        Args:
            elements (List): List of WebElements
            attribute (str): Attribute to extract

        Returns:
            List of extracted attribute values
        """
        return [elem.get_attribute(attribute) for elem in elements]

    def get_total_pages(self) -> int:
        """
        Get total number of pages for pagination

        Returns:
            int: Total number of pages
        """
        self.driver.get(self.base_url)
        page_links = self._find_elements(By.CLASS_NAME, "js-search-link")

        try:
            return int(page_links[-2].text) if page_links else 1
        except (IndexError, ValueError) as e:
            self.logger.warning(f"Could not determine total pages: {e}")
            return 1

    def scrape_products(self) -> List[Dict]:
        """
        Scrape all products across pages

        Returns:
            List of product dictionaries
        """
        all_products = []
        total_pages = self.get_total_pages()

        self.logger.info(f"Scraping {total_pages} pages...")

        for page in range(1, total_pages + 1):
            page_url = f"{self.base_url}?order=product.price.asc&page={page}"
            self.driver.get(page_url)

            # Extract product details
            titles = self._extract_text(
                self._find_elements(By.CLASS_NAME, "product-title")
            )
            references = self._extract_text(
                self._find_elements(By.CLASS_NAME, "product-reference")
            )
            descriptions = self._extract_text(
                self._find_elements(By.CLASS_NAME, "listds")
            )
            prices = self._extract_text(self._find_elements(By.CLASS_NAME, "price"))
            availabilities = self._extract_text(
                self._find_elements(By.ID, "stock_availability")
            )
            img_urls = self._extract_attribute(
                self._find_elements(By.CSS_SELECTOR, "img.center-block"), "src"
            )

            # Combine data
            for i in range(
                min(
                    len(titles),
                    len(references),
                    len(descriptions),
                    len(prices),
                    len(availabilities),
                    len(img_urls),
                )
            ):
                product = {
                    "title": titles[i],
                    "reference": references[i],
                    "description": descriptions[i],
                    "price": prices[i],
                    "availability": availabilities[i],
                    "img_url": img_urls[i],
                }
                all_products.append(product)

            self.logger.info(f"Scraped page {page}: {len(titles)} products found")

        return all_products

    def save_to_json(self, products: List[Dict], filename: str = "products.json"):
        """
        Save scraped products to JSON file

        Args:
            products (List[Dict]): List of product dictionaries
            filename (str): Output filename
        """
        output_path = Path(filename)

        with output_path.open("w", encoding="utf-8") as f:
            json.dump(products, f, ensure_ascii=False, indent=4)

        self.logger.info(f"Saved {len(products)} products to {output_path}")

    def close(self):
        """
        Close the WebDriver
        """
        if self.driver:
            self.driver.quit()


def main():
    log_file = setup_logging()
    scraper = TunisiaNetScraper()
    try:
        products = scraper.scrape_products()
        scraper.save_to_json(products)
    except Exception as e:
        logging.error(f"Scraping failed: {e}", exc_info=True)
    finally:
        scraper.close()


if __name__ == "__main__":
    main()

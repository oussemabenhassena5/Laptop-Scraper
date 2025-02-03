import csv
import json
import logging
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt
import pandas as pd
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

    def save_to_json(
        self, products: List[Dict], filename: str = "results/products.json"
    ):
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

    def save_to_csv(self, products: List[Dict], filename: str = "results/products.csv"):
        """
        Save scraped products to CSV file
        """
        output_path = Path(filename)

        # Define CSV headers
        headers = [
            "title",
            "reference",
            "description",
            "price",
            "availability",
            "img_url",
        ]

        with output_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(products)

        self.logger.info(f"Saved {len(products)} products to CSV: {output_path}")

    def save_to_excel(
        self, products: List[Dict], filename: str = "results/products.xlsx"
    ):
        """
        Save scraped products to Excel file
        """
        df = pd.DataFrame(products)
        output_path = Path(filename)

        # Save to Excel with some styling
        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Products")

            # Auto-adjust columns
            worksheet = writer.sheets["Products"]
            for i, col in enumerate(df.columns):
                column_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
                worksheet.column_dimensions[chr(65 + i)].width = column_len

        self.logger.info(f"Saved {len(products)} products to Excel: {output_path}")

    def generate_markdown_report(
        self, products: List[Dict], filename: str = "results/products_report.md"
    ):
        """
        Generate a markdown report of scraped products
        """
        output_path = Path(filename)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        def clean_price(price_str: str) -> float:
            """
            Clean and convert price string to float
            """
            # Remove any non-numeric characters except decimal point
            import re

            cleaned_price = re.sub(r"[^\d.]", "", price_str)

            try:
                return float(cleaned_price)
            except ValueError:
                self.logger.warning(f"Could not convert price: {price_str}")
                return 0.0

        try:
            # Clean price conversion
            prices = [clean_price(p["price"]) for p in products]
            prices = [p / 1000 for p in prices]

            with output_path.open("w", encoding="utf-8") as f:
                # Report header
                f.write("# TunisiaNet Laptop Scraping Report\n")
                f.write(f"**Total Products Scraped:** {len(products)}\n\n")

                # Price statistics
                f.write("## Price Analysis\n")
                f.write(f"- **Minimum Price:** {min(prices) } DT\n")
                f.write(f"- **Maximum Price:** {max(prices)} DT\n")
                f.write(f"- **Average Price:** {sum(prices)/len(prices):.2f} DT\n\n")

                # Product table
                f.write("## Product Details\n")
                f.write("| Title | Reference | Price | Availability |\n")
                f.write("|-------|-----------|-------|-------------|\n")

                for product in products[:50]:  # Limit to first 50 products
                    # Escape pipe characters in title to prevent markdown table breaking
                    safe_title = product["title"].replace("|", "\\|")
                    f.write(
                        f"| {safe_title} | {product['reference']} | {product['price']} | {product['availability']} |\n"
                    )

            self.logger.info(f"Generated markdown report: {output_path}")

        except Exception as e:
            self.logger.error(f"Error generating markdown report: {e}", exc_info=True)

    def save_to_sqlite(
        self, products: List[Dict], filename: str = "results/products.db"
    ):
        """
        Save scraped products to SQLite database
        """
        output_path = Path(filename)

        # Connect to SQLite database
        conn = sqlite3.connect(str(output_path))
        cursor = conn.cursor()

        # Create table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
                title TEXT,
                reference TEXT PRIMARY KEY,
                description TEXT,
                price TEXT,
                availability TEXT,
                img_url TEXT
            )
        """
        )

        # Insert products
        for product in products:
            try:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO products 
                    (title, reference, description, price, availability, img_url) 
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    tuple(product.values()),
                )
            except sqlite3.IntegrityError:
                self.logger.warning(f"Duplicate product: {product['reference']}")

        # Commit and close
        conn.commit()
        conn.close()

        self.logger.info(
            f"Saved {len(products)} products to SQLite database: {output_path}"
        )

    def generate_price_distribution(
        self, products: List[Dict], filename: str = "results/price_distribution.png"
    ):
        """
        Generate a price distribution plot
        """
        import matplotlib.pyplot as plt
        import re

        def clean_price(price_str: str) -> float:
            """
            Clean and convert price string to float
            """
            # Remove any non-numeric characters except decimal point
            cleaned_price = re.sub(r"[^\d.]", "", price_str)

            try:
                return float(cleaned_price)
            except ValueError:
                self.logger.warning(f"Could not convert price: {price_str}")
                return 0.0

        # Ensure results directory exists
        output_path = Path(filename)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Extract prices, converting to numeric
            prices = [clean_price(p["price"]) for p in products]
            prices = [p / 1000 for p in prices]

            # Remove zero values
            prices = [p for p in prices if p > 0]

            plt.figure(figsize=(12, 7))
            plt.hist(prices, bins=30, edgecolor="black", alpha=0.7)
            plt.title("Laptop Price Distribution in TunisiaNet", fontsize=16)
            plt.xlabel("Price (DT)", fontsize=12)
            plt.ylabel("Number of Products", fontsize=12)
            plt.grid(axis="y", linestyle="--", alpha=0.7)

            # Add some statistical annotations
            plt.axvline(
                sum(prices) / len(prices),
                color="r",
                linestyle="dashed",
                linewidth=2,
                label="Mean Price",
            )

            plt.legend()
            plt.tight_layout()
            plt.savefig(str(output_path), dpi=300)
            plt.close()

            self.logger.info(f"Generated price distribution plot: {output_path}")

        except Exception as e:
            self.logger.error(
                f"Error generating price distribution plot: {e}", exc_info=True
            )

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
        scraper.save_to_csv(products)
        scraper.save_to_excel(products)
        scraper.generate_markdown_report(products)
        scraper.save_to_sqlite(products)
        scraper.generate_price_distribution(products)

    except Exception as e:
        logging.error(f"Scraping failed: {e}", exc_info=True)
    finally:
        scraper.close()


if __name__ == "__main__":
    main()

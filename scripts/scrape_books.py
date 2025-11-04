"""Scrape the books.toscrape.com catalogue into a structured CSV file."""

from __future__ import annotations

import argparse
import csv
import logging
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Iterator, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, Tag

LOGGER = logging.getLogger("books_scraper")

BASE_URL = "https://books.toscrape.com/"
CATALOGUE_ROOT = urljoin(BASE_URL, "catalogue/")
RATING_MAP = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; TechChallengeScraper/1.0; +https://github.com/)"
}
CSV_FIELDS = [
    "id",
    "title",
    "price",
    "currency",
    "rating",
    "availability",
    "category",
    "product_page_url",
    "image_url",
    "description",
    "upc",
    "stock",
]


@dataclass
class ScraperConfig:
    base_url: str = BASE_URL
    sleep_between_requests: float = 0.1
    timeout: int = 30
    output_path: Path = Path("data") / "books_raw.csv"


class BookScraper:
    def __init__(self, config: ScraperConfig) -> None:
        self.config = config
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)

    def run(self) -> int:
        self.config.output_path.parent.mkdir(parents=True, exist_ok=True)
        total_items = 0
        with self.config.output_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
            writer.writeheader()
            for book in self.iter_books():
                total_items += 1
                writer.writerow(book)
        return total_items

    def iter_books(self) -> Iterator[Dict[str, object]]:
        book_id = 1
        for category in self.fetch_categories():
            LOGGER.info("Scraping category '%s'", category.name)
            for book in self.fetch_category_books(category):
                book_record = book.copy()
                book_record["id"] = book_id
                book_record.setdefault("currency", "GBP")
                yield book_record
                book_id += 1

    def fetch_categories(self) -> Iterable["Category"]:
        response = self.session.get(self.config.base_url, timeout=self.config.timeout)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        container = soup.select_one(".side_categories ul")
        if not container:
            raise RuntimeError("Unable to locate categories on landing page")

        for link in container.select("li ul li a"):
            name = link.get_text(strip=True)
            href = urljoin(self.config.base_url, link.get("href"))
            yield Category(name=name, url=href)

    def fetch_category_books(self, category: "Category") -> Iterator[Dict[str, object]]:
        next_page: Optional[str] = category.url
        while next_page:
            response = self.session.get(next_page, timeout=self.config.timeout)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            for article in soup.select("article.product_pod"):
                yield self.parse_book(article, category)
                time.sleep(self.config.sleep_between_requests)

            next_link = soup.select_one("li.next a")
            next_page = urljoin(next_page, next_link.get("href")) if next_link else None

    def parse_book(self, article: Tag, category: "Category") -> Dict[str, object]:
        title_element = article.select_one("h3 a")
        if not title_element:
            raise RuntimeError("Book entry missing title link")

        title = title_element.get("title") or title_element.get_text(strip=True)
        relative_detail = title_element.get("href")
        detail_url = urljoin(category.url, relative_detail)

        price_element = article.select_one("p.price_color")
        price_text = price_element.get_text(strip=True) if price_element else "£0.00"
        price_value = _parse_price(price_text)

        rating_element = article.select_one("p.star-rating")
        rating_classes = rating_element.get("class") if rating_element else []
        rating_text_candidates = [cls for cls in (rating_classes or []) if cls in RATING_MAP]
        rating = RATING_MAP.get(rating_text_candidates[0], 0) if rating_text_candidates else 0

        availability_element = article.select_one("p.instock.availability")
        availability_text = availability_element.get_text(strip=True) if availability_element else ""

        image_element = article.select_one("img")
        image_url = urljoin(BASE_URL, image_element.get("src") if image_element else "")

        details = self.fetch_book_details(detail_url)

        return {
            "title": title,
            "price": round(price_value, 2),
            "currency": "GBP",
            "rating": rating,
            "availability": availability_text,
            "category": category.name,
            "product_page_url": detail_url,
            "image_url": image_url,
            "description": details.description,
            "upc": details.upc,
            "stock": details.stock,
        }

    def fetch_book_details(self, url: str) -> "BookDetails":
        try:
            response = self.session.get(url, timeout=self.config.timeout)
            response.raise_for_status()
        except requests.HTTPError as exc:
            LOGGER.warning("Failed to fetch book details %s: %s", url, exc)
            return BookDetails(description=None, upc=None, stock=None)

        soup = BeautifulSoup(response.text, "html.parser")

        description_block = soup.select_one("#product_description")
        description = ""
        if description_block:
            sibling = description_block.find_next_sibling("p")
            description = sibling.get_text(strip=True) if sibling else ""

        info_table = soup.select_one("table.table.table-striped")
        upc = None
        stock = None
        if info_table:
            for row in info_table.select("tr"):
                header = row.select_one("th")
                value = row.select_one("td")
                if not header or not value:
                    continue
                label = header.get_text(strip=True)
                if label == "UPC":
                    upc = value.get_text(strip=True)
                if label == "Availability":
                    stock = _extract_stock_from_text(value.get_text(strip=True))

        return BookDetails(description=description or None, upc=upc, stock=stock)


@dataclass
class Category:
    name: str
    url: str


@dataclass
class BookDetails:
    description: Optional[str]
    upc: Optional[str]
    stock: Optional[int]


def _extract_stock_from_text(value: str) -> Optional[int]:
    digits = "".join(ch for ch in value if ch.isdigit())
    return int(digits) if digits else None


def _parse_price(value: str) -> float:
    """Normalize a price string into a float, stripping stray symbols."""

    cleaned = value.strip().replace(",", "")
    cleaned = cleaned.replace("Â", "").replace("£", "").replace("GBP", "")
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)", cleaned)
    if not match:
        raise ValueError(f"Unable to parse price from '{value}'")
    return float(match.group(1))


def configure_logging(verbosity: int) -> None:
    level = logging.WARNING
    if verbosity == 1:
        level = logging.INFO
    elif verbosity >= 2:
        level = logging.DEBUG
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(message)s")


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape books.toscrape.com into CSV")
    parser.add_argument(
        "--output",
        default=str(ScraperConfig().output_path),
        help="Where to write the CSV file (default: data/books_raw.csv)",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=ScraperConfig().sleep_between_requests,
        help="Seconds to sleep between each book request (default: 0.1)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=ScraperConfig().timeout,
        help="Request timeout in seconds (default: 30)",
    )
    parser.add_argument(
        "--base-url",
        default=ScraperConfig().base_url,
        help="Alternative base URL (useful for mirrors or local testing)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase log verbosity (-v for INFO, -vv for DEBUG)",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    configure_logging(args.verbose)

    config = ScraperConfig(
        base_url=args.base_url,
        sleep_between_requests=args.sleep,
        timeout=args.timeout,
        output_path=Path(args.output).resolve(),
    )

    scraper = BookScraper(config)
    try:
        total = scraper.run()
    except Exception as exc:  # noqa: BLE001 - top-level exception handler for CLI
        LOGGER.exception("Scraping failed: %s", exc)
        return 1

    LOGGER.info("Scraping completed successfully with %s records", total)
    return 0


if __name__ == "__main__":
    sys.exit(main())

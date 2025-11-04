"""Pytest fixtures for the books API."""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import Iterator

import pytest
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from api.config import override_settings
from api.database import ensure_database
from api.main import create_app

CSV_HEADERS = [
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


@pytest.fixture(name="client")
def fixture_client(tmp_path: Path) -> Iterator[TestClient]:
    csv_path = tmp_path / "books_raw.csv"
    db_path = tmp_path / "books.db"

    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_HEADERS)
        writer.writeheader()
        writer.writerows(
            [
                {
                    "id": 1,
                    "title": "Deep Learning with Python",
                    "price": 45.99,
                    "currency": "GBP",
                    "rating": 5,
                    "availability": "In stock",
                    "category": "Computing",
                    "product_page_url": "https://example.com/book/1",
                    "image_url": "https://example.com/images/1.jpg",
                    "description": "Comprehensive guide to neural networks.",
                    "upc": "ABC123",
                    "stock": 10,
                },
                {
                    "id": 2,
                    "title": "Data Science Fundamentals",
                    "price": 30.50,
                    "currency": "GBP",
                    "rating": 4,
                    "availability": "In stock",
                    "category": "Computing",
                    "product_page_url": "https://example.com/book/2",
                    "image_url": "https://example.com/images/2.jpg",
                    "description": "Introductory data science concepts.",
                    "upc": "DEF456",
                    "stock": 5,
                },
                {
                    "id": 3,
                    "title": "Cooking 101",
                    "price": 18.00,
                    "currency": "GBP",
                    "rating": 3,
                    "availability": "Limited availability",
                    "category": "Cooking",
                    "product_page_url": "https://example.com/book/3",
                    "image_url": "https://example.com/images/3.jpg",
                    "description": "Beginner-friendly recipes.",
                    "upc": "GHI789",
                    "stock": 2,
                },
            ]
        )

    settings = override_settings(
        data_dir=tmp_path,
        csv_filename=csv_path.name,
        db_filename=db_path.name,
        rebuild_db_on_startup=False,
    )

    ensure_database(settings)
    app = create_app(settings)

    client = TestClient(app)
    try:
        yield client
    finally:
        client.close()

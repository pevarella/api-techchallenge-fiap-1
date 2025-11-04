from __future__ import annotations

import csv
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from api.config import override_settings
from api.database import ensure_database
from api.main import create_app

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


def main() -> None:
    csv_path = ROOT_DIR / "tests" / "tmp_books.csv"
    db_path = ROOT_DIR / "tests" / "tmp_books.db"
    csv_path.parent.mkdir(exist_ok=True)

    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerow(
            {
                "id": 1,
                "title": "Data Science Fundamentals",
                "price": 30.5,
                "currency": "GBP",
                "rating": 4,
                "availability": "In stock",
                "category": "Computing",
                "product_page_url": "https://example.com/book/1",
                "image_url": "https://example.com/img/1.jpg",
                "description": "",
                "upc": "123",
                "stock": 5,
            }
        )

    settings = override_settings(
        data_dir=csv_path.parent,
        csv_filename=csv_path.name,
        db_filename=db_path.name,
        rebuild_db_on_startup=False,
    )
    ensure_database(settings)
    app = create_app(settings)
    client = TestClient(app)

    try:
        response = client.get("/api/v1/books/search", params={"title": "data"})
        print("search status:", response.status_code)
        print(response.json())

        response = client.get(
            "/api/v1/books/price-range",
            params={"min_price": 20, "max_price": 50},
        )
        print("price-range status:", response.status_code)
        print(response.json())
    finally:
        client.close()
        db_path.unlink(missing_ok=True)
        csv_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()

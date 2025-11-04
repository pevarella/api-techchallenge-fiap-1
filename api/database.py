"""Database helpers for the books catalogue API."""

from __future__ import annotations

import csv
import logging
import sqlite3
from pathlib import Path
from typing import Dict, Iterable, Iterator

from .config import Settings

LOGGER = logging.getLogger(__name__)

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    price REAL NOT NULL,
    currency TEXT NOT NULL,
    rating INTEGER NOT NULL,
    availability TEXT NOT NULL,
    category TEXT NOT NULL,
    product_page_url TEXT NOT NULL,
    image_url TEXT NOT NULL,
    description TEXT,
    upc TEXT,
    stock INTEGER
);
"""

CREATE_INDICES_SQL = (
    "CREATE INDEX IF NOT EXISTS idx_books_category ON books(category);",
    "CREATE INDEX IF NOT EXISTS idx_books_rating ON books(rating);",
    "CREATE INDEX IF NOT EXISTS idx_books_title ON books(title);",
)

CREATE_PREDICTIONS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS model_predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_name TEXT NOT NULL,
    model_version TEXT,
    created_at TEXT NOT NULL,
    payload TEXT NOT NULL
);
"""

CREATE_PREDICTIONS_INDICES_SQL = (
    "CREATE INDEX IF NOT EXISTS idx_predictions_model_name ON model_predictions(model_name);",
    "CREATE INDEX IF NOT EXISTS idx_predictions_created_at ON model_predictions(created_at);",
)

CSV_REQUIRED_COLUMNS = (
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
)


def ensure_database(settings: Settings) -> None:
    """Create the SQLite catalogue from the CSV file when required."""

    db_path = settings.db_path
    csv_path = settings.csv_path
    db_path.parent.mkdir(parents=True, exist_ok=True)

    if settings.rebuild_db_on_startup and db_path.exists():
        LOGGER.info("Removing existing database at %s", db_path)
        db_path.unlink()

    if db_path.exists():
        LOGGER.debug("SQLite database already present at %s", db_path)
        with get_connection(db_path) as connection:
            _ensure_schema(connection)
        return

    if not csv_path.exists():
        msg = (
            f"CSV file not found at {csv_path}. Run scripts/scrape_books.py before "
            "starting the API or provide a custom BOOKS_CSV_FILENAME."
        )
        raise FileNotFoundError(msg)

    LOGGER.info("Bootstrapping SQLite database from %s", csv_path)
    rows = list(_read_rows_from_csv(csv_path))

    if not rows:
        raise RuntimeError("No data found in CSV. Scraping step may have failed.")

    _write_rows_to_db(rows, db_path)
    LOGGER.info("Database created with %s records", len(rows))


def get_connection(db_path: Path) -> sqlite3.Connection:
    """Return a SQLite connection with row factory configured for dict output."""

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def _read_rows_from_csv(csv_path: Path) -> Iterable[Dict[str, object]]:
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)

        missing_columns = set(CSV_REQUIRED_COLUMNS) - set(reader.fieldnames or [])
        if missing_columns:
            raise RuntimeError(
                f"CSV file at {csv_path} is missing required columns: {sorted(missing_columns)}"
            )

        for row in reader:
            yield {
                "id": int(row["id"]),
                "title": row["title"].strip(),
                "price": float(row["price"]),
                "currency": row["currency"].strip() or "GBP",
                "rating": int(row["rating"]),
                "availability": row["availability"].strip(),
                "category": row["category"].strip(),
                "product_page_url": row["product_page_url"].strip(),
                "image_url": row["image_url"].strip(),
                "description": (row.get("description") or "").strip(),
                "upc": (row.get("upc") or "").strip() or None,
                "stock": int(row["stock"]) if row.get("stock") else None,
            }


def _write_rows_to_db(rows: Iterable[Dict[str, object]], db_path: Path) -> None:
    with get_connection(db_path) as connection:
        _ensure_schema(connection)

        records = list(rows)
        if records:
            cursor = connection.cursor()
            cursor.executemany(
                """
                INSERT OR REPLACE INTO books (
                    id, title, price, currency, rating, availability, category,
                    product_page_url, image_url, description, upc, stock
                ) VALUES (
                    :id, :title, :price, :currency, :rating, :availability, :category,
                    :product_page_url, :image_url, :description, :upc, :stock
                )
                """,
                records,
            )
        connection.commit()


def _ensure_schema(connection: sqlite3.Connection) -> None:
    cursor = connection.cursor()
    cursor.execute(CREATE_TABLE_SQL)
    for statement in CREATE_INDICES_SQL:
        cursor.execute(statement)

    cursor.execute(CREATE_PREDICTIONS_TABLE_SQL)
    for statement in CREATE_PREDICTIONS_INDICES_SQL:
        cursor.execute(statement)
    connection.commit()

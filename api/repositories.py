"""Database access layer for the books catalogue."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any, Dict, Iterable, Optional, Tuple


def row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    """Convert a SQLite row into a plain dictionary."""

    return {key: row[key] for key in row.keys()}


def count_books(connection: sqlite3.Connection) -> int:
    cursor = connection.execute("SELECT COUNT(*) AS total FROM books")
    record = cursor.fetchone()
    return int(record["total"]) if record is not None else 0


def _build_filters(
    category: Optional[str] = None,
    min_rating: Optional[int] = None,
    max_rating: Optional[int] = None,
) -> Tuple[str, list[Any]]:
    fragments = ["WHERE 1 = 1"]
    params: list[Any] = []

    if category:
        fragments.append("AND lower(category) = lower(?)")
        params.append(category)

    if min_rating is not None:
        fragments.append("AND rating >= ?")
        params.append(min_rating)

    if max_rating is not None:
        fragments.append("AND rating <= ?")
        params.append(max_rating)

    return " ".join(fragments), params


def list_books(
    connection: sqlite3.Connection,
    offset: int,
    limit: int,
    category: Optional[str] = None,
    min_rating: Optional[int] = None,
    max_rating: Optional[int] = None,
) -> Iterable[Dict[str, Any]]:
    filter_clause, params = _build_filters(category, min_rating, max_rating)
    sql = (
        "SELECT * FROM books "
        f"{filter_clause} "
        "ORDER BY id ASC LIMIT ? OFFSET ?"
    )
    cursor = connection.execute(sql, [*params, limit, offset])
    return [row_to_dict(row) for row in cursor.fetchall()]


def count_books_filtered(
    connection: sqlite3.Connection,
    category: Optional[str] = None,
    min_rating: Optional[int] = None,
    max_rating: Optional[int] = None,
) -> int:
    filter_clause, params = _build_filters(category, min_rating, max_rating)
    sql = f"SELECT COUNT(*) AS total FROM books {filter_clause}"
    cursor = connection.execute(sql, params)
    record = cursor.fetchone()
    return int(record["total"]) if record else 0


def get_book(connection: sqlite3.Connection, book_id: int) -> Optional[Dict[str, Any]]:
    cursor = connection.execute("SELECT * FROM books WHERE id = ?", (book_id,))
    row = cursor.fetchone()
    return row_to_dict(row) if row else None


def search_books(
    connection: sqlite3.Connection,
    title: Optional[str] = None,
    category: Optional[str] = None,
) -> Iterable[Dict[str, Any]]:
    query = ["SELECT * FROM books WHERE 1 = 1"]
    params: list[Any] = []

    if title:
        query.append("AND lower(title) LIKE lower(?)")
        params.append(f"%{title}%")

    if category:
        query.append("AND lower(category) = lower(?)")
        params.append(category)

    query.append("ORDER BY rating DESC, price ASC")
    cursor = connection.execute(" ".join(query), params)
    return [row_to_dict(row) for row in cursor.fetchall()]


def list_categories(connection: sqlite3.Connection) -> Iterable[str]:
    cursor = connection.execute(
        "SELECT DISTINCT category FROM books ORDER BY lower(category) ASC"
    )
    return [row["category"] for row in cursor.fetchall()]


def stats_overview(connection: sqlite3.Connection) -> Dict[str, Any]:
    cursor = connection.execute(
        """
        SELECT
            COUNT(*) AS total_books,
            AVG(price) AS average_price,
            AVG(rating) AS average_rating,
            MIN(price) AS min_price,
            MAX(price) AS max_price
        FROM books
        """
    )
    row = cursor.fetchone()
    if row is None:
        return {"total_books": 0, "average_price": 0.0, "average_rating": 0.0, "min_price": 0.0, "max_price": 0.0}
    return {
        "total_books": int(row["total_books"] or 0),
        "average_price": float(row["average_price"] or 0.0),
        "average_rating": float(row["average_rating"] or 0.0),
        "min_price": float(row["min_price"] or 0.0),
        "max_price": float(row["max_price"] or 0.0),
    }


def stats_by_category(connection: sqlite3.Connection) -> Iterable[Dict[str, Any]]:
    cursor = connection.execute(
        """
        SELECT
            category,
            COUNT(*) AS book_count,
            AVG(price) AS average_price,
            AVG(rating) AS average_rating
        FROM books
        GROUP BY category
        ORDER BY book_count DESC
        """
    )
    return [row_to_dict(row) for row in cursor.fetchall()]


def top_rated_books(connection: sqlite3.Connection, limit: int = 10) -> Iterable[Dict[str, Any]]:
    cursor = connection.execute(
        """
        SELECT *
        FROM books
        ORDER BY rating DESC, price ASC
        LIMIT ?
        """,
        (limit,),
    )
    return [row_to_dict(row) for row in cursor.fetchall()]


def books_in_price_range(
    connection: sqlite3.Connection,
    min_price: float,
    max_price: float,
) -> Iterable[Dict[str, Any]]:
    cursor = connection.execute(
        """
        SELECT *
        FROM books
        WHERE price BETWEEN ? AND ?
        ORDER BY price ASC
        """,
        (min_price, max_price),
    )
    return [row_to_dict(row) for row in cursor.fetchall()]


def get_all_books(connection: sqlite3.Connection) -> Iterable[Dict[str, Any]]:
    cursor = connection.execute("SELECT * FROM books ORDER BY id ASC")
    return [row_to_dict(row) for row in cursor.fetchall()]


def store_prediction_record(connection: sqlite3.Connection, payload: Dict[str, Any]) -> Dict[str, Any]:
    timestamp = payload.get("created_at") or datetime.utcnow().isoformat()
    persisted_payload = {**payload, "created_at": timestamp}
    cursor = connection.execute(
        """
        INSERT INTO model_predictions (model_name, model_version, created_at, payload)
        VALUES (?, ?, ?, ?)
        """,
        (
            persisted_payload.get("model_name"),
            persisted_payload.get("model_version"),
            timestamp,
            json.dumps(persisted_payload),
        ),
    )
    connection.commit()
    return {"id": int(cursor.lastrowid), "created_at": timestamp}

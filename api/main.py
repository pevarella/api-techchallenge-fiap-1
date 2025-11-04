"""FastAPI entrypoint exposing the books catalogue endpoints."""

from __future__ import annotations

import logging
import sqlite3
from typing import Iterator, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from . import repositories, schemas
from .config import Settings, get_settings
from .database import ensure_database, get_connection

LOGGER = logging.getLogger(__name__)


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    settings = settings or get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        description=settings.description,
        openapi_url=f"{settings.api_prefix}/openapi.json",
        docs_url=f"{settings.api_prefix}/docs",
        redoc_url=f"{settings.api_prefix}/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    def startup() -> None:  # pragma: no cover - exercised via integration tests
        try:
            ensure_database(settings)
        except FileNotFoundError as exc:  # Defensive: missing CSV is a setup issue
            LOGGER.error("Startup aborted: %s", exc)
            raise

    def get_db() -> Iterator[sqlite3.Connection]:
        connection = get_connection(settings.db_path)
        try:
            yield connection
        finally:
            connection.close()

    @app.get(f"{settings.api_prefix}/health", response_model=schemas.HealthStatus)
    def health(db: sqlite3.Connection = Depends(get_db)) -> schemas.HealthStatus:
        total = repositories.count_books(db)
        return schemas.HealthStatus(
            status="ok" if total > 0 else "empty",
            dataset_records=total,
            database_path=str(settings.db_path),
        )

    @app.get(
        f"{settings.api_prefix}/books",
        response_model=schemas.BookCollection,
        summary="List all books with optional filters",
    )
    def list_books(
        offset: int = Query(default=0, ge=0),
        limit: int = Query(default=None, ge=1),
        category: Optional[str] = Query(default=None, description="Exact category match"),
        min_rating: Optional[int] = Query(default=None, ge=0, le=5),
        max_rating: Optional[int] = Query(default=None, ge=0, le=5),
        db: sqlite3.Connection = Depends(get_db),
    ) -> schemas.BookCollection:
        effective_limit = limit or settings.default_page_size
        effective_limit = min(effective_limit, settings.max_page_size)

        total = repositories.count_books_filtered(db, category, min_rating, max_rating)
        books = repositories.list_books(db, offset, effective_limit, category, min_rating, max_rating)
        items = [schemas.Book(**book) for book in books]
        return schemas.BookCollection(
            total=total,
            limit=effective_limit,
            offset=offset,
            items=items,
        )

    @app.get(
        f"{settings.api_prefix}/books/search",
        response_model=list[schemas.Book],
        summary="Search books by partial title and optional category",
    )
    def search_books(
        title: Optional[str] = Query(default=None, min_length=1),
        category: Optional[str] = Query(default=None),
        limit: int = Query(default=50, ge=1, le=200),
        db: sqlite3.Connection = Depends(get_db),
    ) -> list[schemas.Book]:
        results = repositories.search_books(db, title=title, category=category)
        books = [schemas.Book(**book) for book in results][:limit]
        return books

    @app.get(
        f"{settings.api_prefix}/books/top-rated",
        response_model=list[schemas.Book],
        summary="Top rated books in the catalogue",
    )
    def top_rated(
        limit: int = Query(default=10, ge=1, le=100),
        db: sqlite3.Connection = Depends(get_db),
    ) -> list[schemas.Book]:
        results = repositories.top_rated_books(db, limit=limit)
        return [schemas.Book(**book) for book in results]

    @app.get(
        f"{settings.api_prefix}/books/price-range",
        response_model=list[schemas.Book],
        summary="Books within a specific price range",
    )
    def books_in_price_range(
        min_price: float = Query(..., ge=0.0),
        max_price: float = Query(..., ge=0.0),
        db: sqlite3.Connection = Depends(get_db),
    ) -> list[schemas.Book]:
        if max_price < min_price:
            raise HTTPException(status_code=400, detail="max must be greater than or equal to min")
        results = repositories.books_in_price_range(db, min_price=min_price, max_price=max_price)
        return [schemas.Book(**book) for book in results]

    @app.get(
        f"{settings.api_prefix}/books/{{book_id}}",
        response_model=schemas.Book,
        summary="Retrieve a single book by its unique identifier",
    )
    def get_book(book_id: int, db: sqlite3.Connection = Depends(get_db)) -> schemas.Book:
        book = repositories.get_book(db, book_id)
        if not book:
            raise HTTPException(status_code=404, detail=f"Book with id {book_id} not found")
        return schemas.Book(**book)

    @app.get(
        f"{settings.api_prefix}/categories",
        response_model=schemas.CategoryList,
        summary="List all categories present in the dataset",
    )
    def list_categories(db: sqlite3.Connection = Depends(get_db)) -> schemas.CategoryList:
        categories = repositories.list_categories(db)
        return schemas.CategoryList(total=len(categories), items=list(categories))

    @app.get(
        f"{settings.api_prefix}/stats/overview",
        response_model=schemas.StatsOverview,
        summary="Dataset-wide statistics",
    )
    def stats_overview(db: sqlite3.Connection = Depends(get_db)) -> schemas.StatsOverview:
        stats = repositories.stats_overview(db)
        if stats["total_books"] == 0:
            return schemas.StatsOverview(
                total_books=0,
                average_price=0.0,
                average_rating=0.0,
                min_price=0.0,
                max_price=0.0,
            )
        return schemas.StatsOverview(**stats)

    @app.get(
        f"{settings.api_prefix}/stats/categories",
        response_model=schemas.CategoryStatsCollection,
        summary="Category level insights",
    )
    def stats_categories(db: sqlite3.Connection = Depends(get_db)) -> schemas.CategoryStatsCollection:
        stats = [schemas.CategoryStats(**row) for row in repositories.stats_by_category(db)]
        return schemas.CategoryStatsCollection(total=len(stats), items=stats)

    return app


app = create_app()

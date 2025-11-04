"""Pydantic models exposed by the API."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class Book(BaseModel):
    id: int
    title: str
    price: float = Field(description="Monetary value in the recorded currency")
    currency: str = Field(default="GBP", max_length=3)
    rating: int = Field(ge=0, le=5)
    availability: str
    category: str
    product_page_url: HttpUrl
    image_url: HttpUrl
    description: Optional[str] = Field(default=None)
    upc: Optional[str] = Field(default=None)
    stock: Optional[int] = Field(default=None, ge=0)


class BookCollection(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[Book]


class CategoryList(BaseModel):
    total: int
    items: list[str]


class HealthStatus(BaseModel):
    status: str
    dataset_records: int
    database_path: str


class StatsOverview(BaseModel):
    total_books: int
    average_price: float
    average_rating: float
    min_price: float
    max_price: float


class CategoryStats(BaseModel):
    category: str
    book_count: int
    average_price: float
    average_rating: float


class CategoryStatsCollection(BaseModel):
    total: int
    items: list[CategoryStats]

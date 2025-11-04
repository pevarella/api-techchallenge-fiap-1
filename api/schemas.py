"""Pydantic models exposed by the API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

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


class FeatureVector(BaseModel):
    book_id: int
    title: str
    category: str
    price: float
    stock: Optional[int]
    is_available: bool
    availability: str
    title_length: int
    description_length: int


class FeatureCollection(BaseModel):
    total: int
    items: list[FeatureVector]


class TrainingSample(FeatureVector):
    target_rating: int


class TrainingDataset(BaseModel):
    total: int
    items: list[TrainingSample]


class PredictionRequest(BaseModel):
    model_name: str = Field(min_length=1)
    model_version: str = Field(min_length=1)
    inputs: list[dict[str, Any]] = Field(default_factory=list, min_length=1)
    predictions: list[Any] = Field(default_factory=list, min_length=1)
    metadata: Optional[dict[str, Any]] = None


class PredictionResponse(BaseModel):
    id: int
    model_name: str
    model_version: str
    created_at: datetime


class AuthCredentials(BaseModel):
    username: str
    password: str


class TokenPair(BaseModel):
    token_type: Literal["bearer"] = "bearer"
    access_token: str
    refresh_token: str


class RefreshRequest(BaseModel):
    refresh_token: str

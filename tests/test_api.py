"""Integration-style tests for the FastAPI application."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["dataset_records"] == 3


def test_list_books(client: TestClient) -> None:
    response = client.get("/api/v1/books")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 3
    assert len(payload["items"]) == 3


def test_get_book_by_id(client: TestClient) -> None:
    response = client.get("/api/v1/books/2")
    assert response.status_code == 200
    payload = response.json()
    assert payload["title"] == "Data Science Fundamentals"


def test_search_books(client: TestClient) -> None:
    response = client.get("/api/v1/books/search", params={"title": "data"})
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["id"] == 2


def test_categories_endpoint(client: TestClient) -> None:
    response = client.get("/api/v1/categories")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert sorted(payload["items"]) == ["Computing", "Cooking"]


def test_stats_overview(client: TestClient) -> None:
    response = client.get("/api/v1/stats/overview")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total_books"] == 3
    assert round(payload["average_price"], 2) == 31.5


def test_price_range_filter(client: TestClient) -> None:
    response = client.get("/api/v1/books/price-range", params={"min_price": 20, "max_price": 50})
    assert response.status_code == 200
    payload = response.json()
    assert {book["id"] for book in payload} == {1, 2}

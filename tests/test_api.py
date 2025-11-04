"""Integration-style tests for the FastAPI application."""

from __future__ import annotations

from datetime import datetime

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


def test_ml_features_endpoint(client: TestClient) -> None:
    response = client.get("/api/v1/ml/features")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 3
    assert len(payload["items"]) == 3
    first = payload["items"][0]
    assert first["book_id"] == 1
    assert first["is_available"] is True
    assert first["title_length"] == len("Deep Learning with Python")


def test_ml_training_data_endpoint(client: TestClient) -> None:
    response = client.get("/api/v1/ml/training-data")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 3
    assert all(item["target_rating"] >= 0 for item in payload["items"])


def test_ml_predictions_endpoint(client: TestClient) -> None:
    response = client.post(
        "/api/v1/ml/predictions",
        json={
            "model_name": "baseline-recommender",
            "model_version": "1.0.0",
            "inputs": [{"book_id": 1, "features": {"price": 45.99}}],
            "predictions": [{"score": 0.87}],
            "metadata": {"pipeline": "notebook"},
        },
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["model_name"] == "baseline-recommender"
    assert payload["model_version"] == "1.0.0"
    assert payload["id"] > 0
    datetime.fromisoformat(payload["created_at"])

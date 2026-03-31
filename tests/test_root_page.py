from fastapi.testclient import TestClient
from app.main import app


def test_root_page_returns_200():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200


def test_root_page_contains_start_session():
    client = TestClient(app)
    response = client.get("/")
    assert "Start Session" in response.text

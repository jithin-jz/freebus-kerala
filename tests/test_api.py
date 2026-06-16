from app.main import create_app
from fastapi.testclient import TestClient


def test_index_renders():
    client = TestClient(create_app())
    response = client.get("/")
    assert response.status_code == 200
    assert "FreeBus Kerala" in response.text

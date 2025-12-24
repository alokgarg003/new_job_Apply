from fastapi.testclient import TestClient
from webapp.api import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json().get('status') == 'ok'


def test_list_outputs():
    r = client.get("/outputs")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


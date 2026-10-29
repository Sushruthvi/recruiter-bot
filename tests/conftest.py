import pytest
from fastapi.testclient import TestClient

from app.db import get_connection, init_db
from app.main import app
from app.seed import seed


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    """A fresh, seeded database file that the app and the tests both use."""
    path = tmp_path / "test.db"
    monkeypatch.setenv("RECRUITER_DB", str(path))
    conn = get_connection()
    init_db(conn)
    seed(conn)
    conn.close()
    return path


@pytest.fixture
def conn(db_path):
    connection = get_connection()
    yield connection
    connection.close()


@pytest.fixture
def client(db_path):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def ids(client):
    """Look up ids by name, so tests don't depend on insertion order."""
    candidates = {c["name"]: c["id"] for c in client.get("/candidates").json()}
    jobs = {j["title"]: j["id"] for j in client.get("/jobs").json()}
    return {"candidates": candidates, "jobs": jobs}

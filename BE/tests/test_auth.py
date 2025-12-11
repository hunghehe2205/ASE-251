import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.main import app
from app.routers import auth


class FakeUsersCollection:
    """Minimal async-compatible collection for auth tests."""

    def __init__(self, docs=None):
        self.docs = list(docs or [])

    async def find_one(self, query):
        email = query.get("email")
        if email:
            for doc in self.docs:
                if doc.get("email") == email:
                    return doc
        return None

    async def count_documents(self, query):
        user_id_query = query.get("user_id")
        if not user_id_query:
            return 0

        regex = user_id_query.get("$regex")
        if not regex:
            return 0

        prefix = regex.lstrip("^")
        return sum(1 for doc in self.docs if doc.get("user_id", "").startswith(prefix))

    async def insert_one(self, doc):
        self.docs.append(doc)
        return type("InsertOneResult", (), {"inserted_id": doc.get("user_id")})()

    def seed_user(self, doc):
        self.docs.append(doc)


@pytest.fixture
def auth_test_client(monkeypatch):
    fake_collection = FakeUsersCollection()

    async def fake_get_users_collection():
        return fake_collection

    monkeypatch.setattr(auth, "get_users_collection", fake_get_users_collection)

    with TestClient(app) as client:
        yield client, fake_collection


def test_register_success_returns_created_user(auth_test_client, monkeypatch):
    client, _ = auth_test_client

    async def fake_generate_user_id(_):
        return "U2025010001"

    monkeypatch.setattr(auth, "_generate_user_id", fake_generate_user_id)

    payload = {
        "fullname": "Alice",
        "email": "alice@example.com",
        "password": "Secret123",
        "role": "lecturer",
    }

    response = client.post("/auth/register", json=payload)
    assert response.status_code == 201

    body = response.json()
    assert body["data"]["user_id"] == "U2025010001"
    assert body["data"]["email"] == payload["email"]
    assert body["meta"]["message"] == "Registration successful"


def test_register_rejects_duplicate_email(auth_test_client):
    client, fake_collection = auth_test_client

    fake_collection.seed_user(
        {
            "user_id": "U2024010001",
            "fullname": "Existing",
            "email": "taken@example.com",
            "password": auth._hash_password("Topsecret1"),
            "role": "student",
        }
    )

    payload = {
        "fullname": "Bob",
        "email": "taken@example.com",
        "password": "Another123",
        "role": "student",
    }
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EMAIL_ALREADY_EXISTS"


def test_register_rejects_invalid_role(auth_test_client):
    client, _ = auth_test_client

    payload = {
        "fullname": "Carol",
        "email": "carol@example.com",
        "password": "Secret123",
        "role": "admin",
    }
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 422


def test_login_success_with_hashed_password(auth_test_client):
    client, fake_collection = auth_test_client
    fake_collection.seed_user(
        {
            "user_id": "U2024010002",
            "fullname": "Dave",
            "email": "dave@example.com",
            "password": auth._hash_password("Secret123"),
            "role": "lecturer",
        }
    )

    response = client.post(
        "/auth/login", json={"email": "dave@example.com", "password": "Secret123"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["role"] == "lecturer"
    assert body["user_id"] == "U2024010002"


def test_login_rejects_invalid_password(auth_test_client):
    client, fake_collection = auth_test_client
    fake_collection.seed_user(
        {
            "user_id": "U2024010003",
            "fullname": "Eve",
            "email": "eve@example.com",
            "password": auth._hash_password("Correct123"),
            "role": "student",
        }
    )

    response = client.post(
        "/auth/login", json={"email": "eve@example.com", "password": "Wrong999"}
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_login_blocks_blacklisted_user(auth_test_client):
    client, fake_collection = auth_test_client
    fake_collection.seed_user(
        {
            "user_id": "U2024010004",
            "fullname": "Frank",
            "email": "frank@example.com",
            "password": auth._hash_password("Secret123"),
            "role": "student",
            "is_blacklisted": True,
        }
    )

    response = client.post(
        "/auth/login", json={"email": "frank@example.com", "password": "Secret123"}
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN_ROLE"


def test_logout_returns_success():
    with TestClient(app) as client:
        response = client.post("/auth/logout")
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "Logout successful"}

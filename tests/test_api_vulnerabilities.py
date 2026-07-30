import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest
from fastapi.testclient import TestClient
from db_api.main import app
import os

client = TestClient(app)

def test_chat_input_length_limit():
    # Long message (> 500 characters)
    long_msg = "A" * 501
    resp = client.post("/api/chat", json={
        "message": long_msg,
        "user_identifier": "test-user"
    })
    assert resp.status_code == 400
    assert "Message length exceeds 500 characters" in resp.json()["detail"]

    # Valid message
    resp = client.post("/api/chat", json={
        "message": "Hastane randevusu almak istiyorum",
        "user_identifier": "test-user"
    })
    assert resp.status_code == 200


def test_companies_api_authorization():
    # No API Key
    resp = client.get("/api/companies")
    assert resp.status_code == 401

    # Wrong API Key
    resp = client.get("/api/companies", headers={"X-API-Key": "wrong-key"})
    assert resp.status_code == 401

    # Correct API Key
    key = os.getenv("ADMIN_API_KEY", "5e5d3298c56e297a7ef7cd7f4c75908ce90e75a3ba2bf7b75298a08892be804a")
    resp = client.get("/api/companies", headers={"X-API-Key": key})
    assert resp.status_code == 200


def test_seed_api_authorization():
    # No API Key
    resp = client.post("/api/seed")
    assert resp.status_code == 401

    # Correct API Key
    key = os.getenv("ADMIN_API_KEY", "5e5d3298c56e297a7ef7cd7f4c75908ce90e75a3ba2bf7b75298a08892be804a")
    resp = client.post("/api/seed", headers={"X-API-Key": key})
    assert resp.status_code == 200

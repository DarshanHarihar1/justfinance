from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import TEST_PASSWORD


def test_login_sets_cookie_and_me_succeeds(client: TestClient) -> None:
    login = client.post("/api/auth/login", json={"password": TEST_PASSWORD})
    assert login.status_code == 204
    assert client.cookies

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json() == {"authenticated": True}


def test_wrong_password_returns_401(client: TestClient) -> None:
    response = client.post("/api/auth/login", json={"password": "wrong"})
    assert response.status_code == 401


def test_protected_route_requires_auth(client: TestClient) -> None:
    client.cookies.clear()
    response = client.get("/api/categories")
    assert response.status_code == 401
    assert response.json()["error"] == "unauthenticated"


def test_logout_clears_session(client: TestClient) -> None:
    client.post("/api/auth/login", json={"password": TEST_PASSWORD})
    logout = client.post("/api/auth/logout")
    assert logout.status_code == 204
    me = client.get("/api/auth/me")
    assert me.status_code == 401


def test_brute_force_lockout(client: TestClient) -> None:
    from app.auth.bruteforce import reset_all

    reset_all()
    client.cookies.clear()
    for _ in range(10):
        client.post("/api/auth/login", json={"password": "wrong"})
    response = client.post("/api/auth/login", json={"password": "wrong"})
    assert response.status_code == 429
    assert response.headers.get("retry-after") == "300"
    reset_all()

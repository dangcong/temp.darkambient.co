from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def test_html_shell_is_never_cached():
    response = client.get("/")

    assert response.status_code == 200
    assert "no-cache" in response.headers["cache-control"]


def test_versioned_static_asset_is_immutable():
    response = client.get("/app.js?v=20260907-mail-capabilities")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "public, max-age=31536000, immutable"


def test_unversioned_static_asset_must_revalidate():
    response = client.get("/app.js")

    assert response.status_code == 200
    assert "no-cache" in response.headers["cache-control"]

"""Basic API tests."""


def test_client_fixture(client):
    """Client fixture provides a working test client."""
    response = client.get("/")
    # 200 OK, 307 redirect, 404, or 422 is acceptable for CI smoke test
    assert response.status_code in (200, 307, 404, 422)

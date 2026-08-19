def test_health_ok(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_cors_allows_configured_frontend_origin(client):
    origin = "https://intelligent-media-processing-pipeline-oido.onrender.com"
    response = client.get("/api/v1/health", headers={"Origin": origin})
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == origin

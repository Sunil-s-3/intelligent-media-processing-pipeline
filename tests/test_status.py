def test_status_for_valid_processing_id(client, png_file):
    uploaded = client.post("/api/v1/images", files=png_file)
    processing_id = uploaded.json()["processing_id"]

    response = client.get(f"/api/v1/images/{processing_id}/status")
    assert response.status_code == 200
    body = response.json()
    assert body["processing_id"] == processing_id
    assert body["status"] == "pending"


def test_status_unknown_processing_id(client):
    response = client.get("/api/v1/images/00000000-0000-0000-0000-000000000000/status")
    assert response.status_code == 404
    assert response.json()["error"] == "not_found"


def test_results_unknown_processing_id(client):
    response = client.get("/api/v1/images/00000000-0000-0000-0000-000000000000/results")
    assert response.status_code == 404


def test_results_not_ready_while_pending(client, png_file):
    uploaded = client.post("/api/v1/images", files=png_file)
    processing_id = uploaded.json()["processing_id"]
    response = client.get(f"/api/v1/images/{processing_id}/results")
    assert response.status_code == 202
    assert response.json()["status"] == "pending"
    assert response.json()["analysis"] is None

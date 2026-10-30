from io import BytesIO
from unittest.mock import patch

from app import app


def test_preview_deduplicates_for_display():
    client = app.test_client()
    response = client.post("/api/preview", data={"emails": "a@example.com\na@example.com\nb@example.com"})
    assert response.status_code == 200
    assert response.json["total"] == 3
    assert response.json["duplicates"] == 1


def test_csv_preview():
    client = app.test_client()
    response = client.post("/api/preview", data={"file": (BytesIO(b"email\na@example.com\n"), "list.csv")}, content_type="multipart/form-data")
    assert response.status_code == 200
    assert response.json["emails"] == ["a@example.com"]


def test_job_creation_uses_background_worker():
    client = app.test_client()
    with patch("app.threading.Thread") as thread:
        response = client.post("/api/jobs", data={"emails": "a@example.com"})
    assert response.status_code == 200
    thread.return_value.start.assert_called_once()


def test_category_exports_have_only_email_and_verified_columns():
    client = app.test_client()
    with patch("app.threading.Thread"):
        response = client.post("/api/jobs", data={"emails": "a@example.com"})
    job_id = response.json["job_id"]
    from app import jobs, jobs_lock
    with jobs_lock:
        jobs[job_id]["results"] = [
            {"email": "good@example.com", "final_status": "LIKELY_VALID"},
            {"email": "bad@example.com", "final_status": "INVALID"},
            {"email": "maybe@example.com", "final_status": "UNKNOWN"},
        ]
    valid = client.post(f"/api/export/{job_id}/valid")
    invalid = client.post(f"/api/export/{job_id}/invalid")
    assert valid.data.decode() == "email,verified\ngood@example.com,True\n"
    assert invalid.data.decode() == "email,verified\nbad@example.com,False\n"

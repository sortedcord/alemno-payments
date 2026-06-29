import io
import pytest
from httpx import AsyncClient
from app.worker import celery_app

# Mark all tests as async
pytestmark = pytest.mark.asyncio

# Set celery to run tasks eagerly (synchronously) during API testing
celery_app.conf.task_always_eager = True


async def test_upload_csv_success(client: AsyncClient):
    csv_content = (
        "transaction_id,date,amount,category,description\n"
        "TX1001,2026-06-25,120.50,Groceries,Weekly grocery shop\n"
        "TX1002,06/26/2026,15000.00,Electronics,New Laptop\n"  # This will be flagged as anomaly (> $5,000)
    )

    files = {
        "file": (
            "transactions.csv",
            io.BytesIO(csv_content.encode("utf-8")),
            "text/csv",
        )
    }

    # 1. Post upload CSV
    response = await client.post("/api/v1/jobs/upload", files=files)
    assert response.status_code == 201

    data = response.json()
    assert "id" in data
    assert data["filename"] == "transactions.csv"
    assert data["status"] == "pending"  # Initial state returned by router immediately

    job_id = data["id"]

    # Since Celery is in eager mode, the task should have completed immediately.
    # 2. Get Job Status
    status_response = await client.get(f"/api/v1/jobs/{job_id}/status")
    assert status_response.status_code == 200
    status_data = status_response.json()
    assert status_data["id"] == job_id
    assert status_data["status"] == "completed"
    assert status_data["summary"]["total_rows"] == 2
    assert status_data["summary"]["total_amount"] == 15120.50
    assert status_data["summary"]["anomalies_count"] == 1
    assert status_data["summary"]["top_category"] == "Electronics"

    # 3. Get Job Results
    results_response = await client.get(f"/api/v1/jobs/{job_id}/results")
    assert results_response.status_code == 200
    results_data = results_response.json()
    assert results_data["id"] == job_id
    assert results_data["status"] == "completed"

    results = results_data["results"]
    assert len(results["cleaned_transactions"]) == 2
    assert len(results["flagged_anomalies"]) == 1
    assert results["flagged_anomalies"][0]["transaction_id"] == "TX1002"
    assert results["spend_breakdown"]["Groceries"]["total_spend"] == 120.50
    assert "Successfully parsed and processed" in results["narrative_summary"]


async def test_upload_invalid_csv(client: AsyncClient):
    # Invalid CSV structure (missing required column)
    csv_content = (
        "transaction_id,amount,category,description\n"
        "TX1001,120.50,Groceries,Weekly grocery shop\n"
    )
    files = {
        "file": (
            "transactions.csv",
            io.BytesIO(csv_content.encode("utf-8")),
            "text/csv",
        )
    }

    response = await client.post("/api/v1/jobs/upload", files=files)
    assert response.status_code == 400
    assert "Missing required CSV columns" in response.json()["detail"]


async def test_get_nonexistent_job(client: AsyncClient):
    response = await client.get("/api/v1/jobs/nonexistent-id-xyz/status")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


async def test_get_all_jobs(client: AsyncClient):
    response = await client.get("/api/v1/jobs")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

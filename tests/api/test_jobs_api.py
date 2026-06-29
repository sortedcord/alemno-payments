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
        "txn_id,date,amount,merchant,currency,category,account\n"
        "TX1001,2026-06-25,120.50,Weekly grocery shop,INR,Groceries,ACC01\n"
        "TX1002,06/26/2026,6000.00,New Laptop,USD,Electronics,ACC02\n"  # Anomaly (> $5,000 USD equivalent)
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

    summary = status_data["summary"]
    assert summary is not None
    assert summary["anomaly_count"] == 1
    assert (
        summary["total_spend_usd"] > 6000.0
    )  # TX1002 is $6,000, TX1001 is INR 120.50 ($1.45)
    assert "New Laptop" in summary["top_merchants"]
    assert summary["risk_level"] == "Medium"  # 1 anomaly

    # 3. Get Job Results
    results_response = await client.get(f"/api/v1/jobs/{job_id}/results")
    assert results_response.status_code == 200
    results_data = results_response.json()
    assert results_data["id"] == job_id
    assert results_data["status"] == "completed"

    transactions_list = results_data["transactions"]
    assert len(transactions_list) == 2

    # Assert TX1002 is flagged as an anomaly
    laptop_txn = next(t for t in transactions_list if t["txn_id"] == "TX1002")
    assert laptop_txn["is_anomaly"] is True
    assert "High value transaction" in laptop_txn["anomaly_reason"]
    assert laptop_txn["llm_category"] == "Electronics"
    assert laptop_txn["llm_failed"] is False

    grocery_txn = next(t for t in transactions_list if t["txn_id"] == "TX1001")
    assert grocery_txn["is_anomaly"] is False
    assert grocery_txn["currency"] == "INR"


async def test_upload_invalid_csv(client: AsyncClient):
    # Invalid CSV structure (missing required column: merchant)
    csv_content = "txn_id,date,amount\nTX1001,2026-06-25,120.50\n"
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

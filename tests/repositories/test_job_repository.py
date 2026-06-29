from datetime import date
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.job_repository import JobRepository
from app.db.models.transaction import Transaction
from app.db.models.job_summary import JobSummary

# Set up asyncio marker
pytestmark = pytest.mark.asyncio


async def test_create_and_get_job(db_session: AsyncSession):
    repo = JobRepository(db_session)

    # Create job
    job = await repo.create(filename="test_transactions.csv")
    assert job.id is not None
    assert job.status == "pending"
    assert job.filename == "test_transactions.csv"

    # Retrieve job
    fetched_job = await repo.get_by_id(job.id)
    assert fetched_job is not None
    assert fetched_job.id == job.id
    assert fetched_job.filename == "test_transactions.csv"


async def test_update_job_and_add_relations(db_session: AsyncSession):
    repo = JobRepository(db_session)
    job = await repo.create(filename="update_test.csv")

    # Update status and count
    updated = await repo.update(
        job, status="completed", row_count_raw=10, row_count_clean=8
    )
    assert updated.status == "completed"
    assert updated.row_count_raw == 10
    assert updated.row_count_clean == 8

    # Create & add summary
    summary = JobSummary(
        job_id=job.id,
        total_spend_inr=15000.0,
        total_spend_usd=180.72,
        top_merchants={"Merchant A": 100.0},
        anomaly_count=1,
        narrative="Good",
        risk_level="Low",
    )
    await repo.add_summary(summary)

    # Create & add transaction
    txn = Transaction(
        job_id=job.id,
        txn_id="TX001",
        date=date(2026, 6, 25),
        merchant="Merchant A",
        amount=100.0,
        currency="USD",
        status="cleaned",
        is_anomaly=False,
    )
    await repo.add_transactions([txn])

    # Retrieve to verify persistence
    fetched = await repo.get_by_id(job.id)
    assert fetched.status == "completed"
    assert fetched.row_count_raw == 10
    assert fetched.row_count_clean == 8
    assert fetched.summary is not None
    assert fetched.summary.total_spend_usd == 180.72
    assert len(fetched.transactions) == 1
    assert fetched.transactions[0].txn_id == "TX001"


async def test_list_jobs(db_session: AsyncSession):
    repo = JobRepository(db_session)

    await repo.create(filename="list_1.csv")
    await repo.create(filename="list_2.csv")

    jobs = await repo.list_all()
    # At least the ones we created in this test session
    assert len(jobs) >= 2

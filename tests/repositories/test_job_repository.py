import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.job_repository import JobRepository
from app.db.models.job import Job

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


async def test_update_job(db_session: AsyncSession):
    repo = JobRepository(db_session)
    job = await repo.create(filename="update_test.csv")
    
    # Update status and count
    updated = await repo.update(job, status="completed", row_count=10, summary={"total": 100})
    assert updated.status == "completed"
    assert updated.row_count == 10
    assert updated.summary == {"total": 100}
    
    # Retrieve to verify persistence
    fetched = await repo.get_by_id(job.id)
    assert fetched.status == "completed"
    assert fetched.row_count == 10


async def test_list_jobs(db_session: AsyncSession):
    repo = JobRepository(db_session)
    
    # Clear existing if any
    await repo.create(filename="list_1.csv")
    await repo.create(filename="list_2.csv")
    
    jobs = await repo.list_all()
    assert len(jobs) >= 2
    
    pending_jobs = await repo.list_all(status="pending")
    assert len(pending_jobs) >= 2
    
    completed_jobs = await repo.list_all(status="completed")
    assert len(completed_jobs) == 1  # From the update test above

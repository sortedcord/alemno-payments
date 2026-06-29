from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.db.models.job import Job
from app.db.models.transaction import Transaction
from app.db.models.job_summary import JobSummary


class JobRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, filename: str) -> Job:
        """Create a new job record with status='pending'"""
        job = Job(filename=filename, status="pending")
        self.db.add(job)
        await self.db.flush()
        return job

    async def get_by_id(self, job_id: str) -> Optional[Job]:
        """Fetch a job record by its ID, eagerly loading summary and transactions"""
        query = (
            select(Job)
            .options(selectinload(Job.summary), selectinload(Job.transactions))
            .where(Job.id == job_id)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_all(self, status: Optional[str] = None) -> List[Job]:
        """List all job records, optionally filtered by status, eagerly loading summary"""
        query = select(Job).options(selectinload(Job.summary))
        if status:
            query = query.where(Job.status == status)
        query = query.order_by(Job.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update(self, job: Job, **kwargs) -> Job:
        """Update job fields dynamically"""
        for key, value in kwargs.items():
            if hasattr(job, key):
                setattr(job, key, value)
        await self.db.flush()
        return job

    async def add_transactions(self, transactions: List[Transaction]) -> None:
        """Add multiple transaction records in bulk"""
        self.db.add_all(transactions)
        await self.db.flush()

    async def add_summary(self, summary: JobSummary) -> JobSummary:
        """Add job summary record"""
        self.db.add(summary)
        await self.db.flush()
        return summary

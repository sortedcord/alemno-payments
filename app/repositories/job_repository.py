from typing import List, Optional, Any, Dict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.job import Job


class JobRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, filename: str) -> Job:
        job = Job(filename=filename, status="pending")
        self.db.add(job)
        await self.db.flush()
        return job


    async def list_all(self, status: Optional[str] = None) -> List[Job]:
        query = select(Job)
        if status:
            query = query.where(Job.status == status)
        query = query.order_by(Job.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())


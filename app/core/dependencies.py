from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.repositories.job_repository import JobRepository
from app.services.job_service import JobService


def get_job_repository(db: AsyncSession = Depends(get_db)) -> JobRepository:
    """Dependency to retrieve JobRepository"""
    return JobRepository(db)


def get_job_service(repo: JobRepository = Depends(get_job_repository)) -> JobService:
    """Dependency to retrieve JobService"""
    return JobService(repo)

from typing import List, Optional
from app.repositories.job_repository import JobRepository
from app.core.exceptions import JobNotFoundException
from app.db.models.job import Job
from app.utils.csv_parser import parse_and_validate_csv
from app.worker import process_transaction_job


class JobService:
    def __init__(self, repo: JobRepository):
        self.repo = repo

    async def upload_csv(self, filename: str, content: bytes) -> Job:
        parsed_transactions = parse_and_validate_csv(content)

        job = await self.repo.create(filename=filename)

        process_transaction_job.delay(job.id, parsed_transactions)

        return job

    async def get_job_status(self, job_id: str) -> Job:
        job = await self.repo.get_by_id(job_id)
        if not job:
            raise JobNotFoundException(job_id)
        return job

    async def get_job_results(self, job_id: str) -> Job:
        job = await self.repo.get_by_id(job_id)
        if not job:
            raise JobNotFoundException(job_id)
        return job

    async def list_jobs(self, status: Optional[str] = None) -> List[Job]:
        return await self.repo.list_all(status=status)

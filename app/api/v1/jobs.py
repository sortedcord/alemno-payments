from typing import List, Optional
from fastapi import APIRouter, Depends, File, UploadFile, Query, HTTPException, status
from app.core.dependencies import get_job_service
from app.core.exceptions import JobNotFoundException, InvalidCSVException
from app.schemas.job import JobResponse, JobStatusResponse, JobResultResponse
from app.services.job_service import JobService

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/upload", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def upload_csv(
    file: UploadFile = File(...),
    service: JobService = Depends(get_job_service),
):
    if not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files are supported.",
        )

    content = await file.read()
    try:
        job = await service.upload_csv(filename=file.filename, content=content)
        return job
    except InvalidCSVException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    service: JobService = Depends(get_job_service),
):
    try:
        job = await service.get_job_status(job_id)
        return job
    except JobNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get("/{job_id}/results", response_model=JobResultResponse)
async def get_job_result(
    job_id: str,
    service: JobService = Depends(get_job_service),
):
    try:
        job = await service.get_job_results(job_id)
        return job
    except JobNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get("", response_model=List[JobResponse])
async def get_all_jobs(
    status: Optional[str] = Query(None, description="Filter jobs by status"),
    service: JobService = Depends(get_job_service),
):
    return await service.list_jobs(status=status)

from typing import List, Optional
from fastapi import APIRouter, Depends, File, UploadFile, Query, HTTPException, status
from app.core.dependencies import get_job_service
from app.core.exceptions import JobNotFoundException, InvalidCSVException
from app.schemas.job import JobResponse, JobStatusResponse, JobResultResponse
from app.services.job_service import JobService

router = APIRouter(prefix="/jobs", tags=["jobs"])

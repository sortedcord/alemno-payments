from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict


class JobBase(BaseModel):
    filename: str


class JobCreate(JobBase):
    pass


class JobResponse(JobBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str
    row_count: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class JobStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str
    summary: Optional[Dict[str, Any]] = None


class JobResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str
    results: Optional[Dict[str, Any]] = None

from datetime import date, datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    job_id: str
    txn_id: str
    date: date
    merchant: str
    amount: float
    currency: str
    status: Optional[str] = None
    category: Optional[str] = None
    account_id: Optional[str] = None
    is_anomaly: bool
    anomaly_reason: Optional[str] = None
    llm_category: Optional[str] = None
    llm_raw_response: Optional[str] = None
    llm_failed: Optional[bool] = False


class JobSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    job_id: str
    total_spend_inr: float
    total_spend_usd: float
    top_merchants: Dict[str, Any]
    anomaly_count: int
    narrative: Optional[str] = None
    risk_level: Optional[str] = None


class JobBase(BaseModel):
    filename: str


class JobCreate(JobBase):
    pass


class JobResponse(JobBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str
    row_count_raw: Optional[int] = None
    row_count_clean: Optional[int] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class JobStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str
    summary: Optional[JobSummaryResponse] = None


class JobResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str
    summary: Optional[JobSummaryResponse] = None
    transactions: List[TransactionResponse] = []

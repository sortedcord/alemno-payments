from fastapi import HTTPException, status
class AlemnoException(Exception):
    pass
class JobNotFoundException(AlemnoException):
    def __init__(self, job_id: str):
        self.job_id = job_id
        super().__init__(f"Job with ID {job_id} not found")
class InvalidCSVException(AlemnoException):
    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)

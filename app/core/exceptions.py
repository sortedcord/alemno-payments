class AlemnoException(Exception):
    """Base exception for Alemno Payments Application"""

    pass


class JobNotFoundException(AlemnoException):
    """Raised when a job is not found"""

    def __init__(self, job_id: str):
        self.job_id = job_id
        super().__init__(f"Job with ID {job_id} not found")


class InvalidCSVException(AlemnoException):
    """Raised when the uploaded CSV is invalid"""

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)

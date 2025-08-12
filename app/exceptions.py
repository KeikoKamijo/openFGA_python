from typing import Optional
from fastapi import HTTPException


class ResourceNotFoundException(HTTPException):
    def __init__(self, resource_uuid: Optional[str] = None):
        detail = f"Resource {resource_uuid} not found" if resource_uuid else "Resource not found"
        super().__init__(status_code=404, detail=detail)


class PermissionDeniedException(HTTPException):
    def __init__(self, detail: str = "Access denied"):
        super().__init__(status_code=403, detail=detail)


class FGAOperationException(HTTPException):
    def __init__(self, operation: str, detail: str):
        super().__init__(status_code=500, detail=f"FGA {operation} failed: {detail}")


class ValidationException(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status_code=400, detail=detail)
"""
Unified API response format used across ALL endpoints.
Every response follows this structure — no exceptions.
"""

from pydantic import BaseModel
from typing import Any, Optional
from datetime import datetime, timezone
import uuid


class APIResponse(BaseModel):
    success: bool = True
    message: str = "Operation completed successfully."
    data: Optional[Any] = None
    timestamp: str = ""
    request_id: str = ""

    def __init__(self, **data):
        if not data.get("timestamp"):
            data["timestamp"] = datetime.now(timezone.utc).isoformat()
        if not data.get("request_id"):
            data["request_id"] = str(uuid.uuid4())
        super().__init__(**data)


def success_response(data: Any = None, message: str = "Operation completed successfully.") -> dict:
    return APIResponse(success=True, message=message, data=data).model_dump()


def error_response(message: str, data: Any = None) -> dict:
    return APIResponse(success=False, message=message, data=data).model_dump()

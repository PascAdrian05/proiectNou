from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ScanRequest(BaseModel):
    website_id: UUID


class ScanJobResponse(BaseModel):
    task_id: str
    scan_run_id: UUID


class ScanRunRead(BaseModel):
    id: UUID
    website_id: UUID
    status: str
    current_step: str | None = None
    progress: str | None = None
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None
    result_json: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

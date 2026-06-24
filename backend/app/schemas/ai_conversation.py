from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AIConversationCreate(BaseModel):
    conversation_type: str
    messages: str = "[]"
    context_data: str = "{}"


class AIConversationUpdate(BaseModel):
    messages: str
    context_data: str = "{}"


class AIConversationRead(BaseModel):
    id: UUID
    user_id: UUID
    tenant_id: UUID
    conversation_type: str
    messages: str
    context_data: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
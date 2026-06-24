from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from uuid import UUID

from app.core.database import get_session
from app.models.ai_conversation import AIConversation
from app.models.user import User
from app.schemas.ai_conversation import AIConversationCreate, AIConversationUpdate, AIConversationRead
from app.api.deps import get_current_user


router = APIRouter()


@router.get("/", response_model=list[AIConversationRead])
def list_conversations(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    conversations = session.exec(
        select(AIConversation)
        .where(AIConversation.user_id == current_user.id)
        .order_by(AIConversation.updated_at.desc())
    ).all()
    return conversations


@router.get("/{conversation_id}", response_model=AIConversationRead)
def get_conversation(
    conversation_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    conversation = session.get(AIConversation, conversation_id)
    if not conversation or conversation.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return conversation


@router.post("/", response_model=AIConversationRead, status_code=status.HTTP_201_CREATED)
def create_conversation(
    payload: AIConversationCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    conversation = AIConversation(
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        conversation_type=payload.conversation_type,
        messages=payload.messages,
        context_data=payload.context_data,
    )
    session.add(conversation)
    session.commit()
    session.refresh(conversation)
    return conversation


@router.patch("/{conversation_id}", response_model=AIConversationRead)
def update_conversation(
    conversation_id: UUID,
    payload: AIConversationUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    conversation = session.get(AIConversation, conversation_id)
    if not conversation or conversation.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    conversation.messages = payload.messages
    conversation.context_data = payload.context_data
    conversation.updated_at = conversation.updated_at
    session.add(conversation)
    session.commit()
    session.refresh(conversation)
    return conversation


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    conversation = session.get(AIConversation, conversation_id)
    if not conversation or conversation.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    session.delete(conversation)
    session.commit()
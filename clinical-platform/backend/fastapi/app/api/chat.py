# app/api/chat.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from uuid import UUID
from typing import Optional
from ..models.database import get_db
from ..services.auth_context import get_user_context, UserContext
from ..ai import PatientAssistant

router = APIRouter(prefix="/api/chat", tags=["chat"])

assistant = PatientAssistant()


class ChatRequest(BaseModel):
    patient_id: UUID
    message: str
    context: Optional[str] = None


@router.post("/patient")
async def chat_with_patient_assistant(
    req: ChatRequest,
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_user_context),
):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail={"code": "EMPTY_MESSAGE", "message": "Message cannot be empty"})
    response = await assistant.chat(db, req.patient_id, req.message)
    return response.model_dump()

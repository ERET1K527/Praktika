from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.core.deps import get_current_user
from app.models import User
from app.schemas.chat import MessageCreate, MessageOut, ChatOut
from app.services import chat_service

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.get("/chats", response_model=list[ChatOut])
def api_get_chats(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return chat_service.get_user_chats(db, current_user.id)


@router.post("/application/{application_id}", response_model=ChatOut)
def api_create_chat(application_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        chat = chat_service.get_or_create_chat(db, application_id, current_user.id)
        from app.schemas.chat import ChatOut
        from app.models import Vacancy, Candidate, Employer, Application
        application = db.get(Application, chat.application_id)
        vacancy = db.get(Vacancy, application.vacancy_id) if application else None
        candidate = db.get(Candidate, application.candidate_id) if application else None
        candidate_user = db.get(User, candidate.user_id) if candidate else None
        employer = None
        employer_user = None
        if vacancy:
            employer = db.get(Employer, vacancy.employer_id)
            if employer:
                employer_user = db.get(User, employer.user_id)
        other_email = None
        if candidate and candidate.user_id == current_user.id:
            other_email = employer_user.email if employer_user else None
        elif employer and employer.user_id == current_user.id:
            other_email = candidate_user.email if candidate_user else None
        return ChatOut(
            id=chat.id,
            application_id=chat.application_id,
            created_at=chat.created_at,
            vacancy_title=vacancy.title if vacancy else None,
            other_user_email=other_email,
            last_message=None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{chat_id}/messages", response_model=list[MessageOut])
def api_get_messages(chat_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        return chat_service.get_chat_messages(db, chat_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{chat_id}/messages", response_model=MessageOut)
def api_send_message(chat_id: int, data: MessageCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        return chat_service.send_message(db, chat_id, current_user.id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

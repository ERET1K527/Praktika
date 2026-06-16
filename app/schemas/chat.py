from datetime import datetime

from pydantic import BaseModel


class MessageCreate(BaseModel):
    text: str


class MessageOut(BaseModel):
    id: int
    chat_id: int
    sender_id: int
    text: str
    created_at: datetime
    sender_email: str | None = None

    model_config = {"from_attributes": True}


class ChatOut(BaseModel):
    id: int
    application_id: int
    created_at: datetime
    vacancy_title: str | None = None
    other_user_email: str | None = None
    last_message: str | None = None

    model_config = {"from_attributes": True}

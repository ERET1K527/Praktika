from datetime import datetime

from pydantic import BaseModel


class CandidateCreate(BaseModel):
    name: str
    surname: str
    phone: str | None = None
    city: str | None = None
    skills: str | None = None
    experience: str | None = None
    education: str | None = None
    resume: str | None = None


class CandidateUpdate(BaseModel):
    name: str | None = None
    surname: str | None = None
    phone: str | None = None
    city: str | None = None
    skills: str | None = None
    experience: str | None = None
    education: str | None = None
    resume: str | None = None


class CandidateOut(BaseModel):
    id: int
    user_id: int
    name: str
    surname: str
    phone: str | None
    city: str | None
    skills: str | None
    experience: str | None
    education: str | None
    resume: str | None

    model_config = {"from_attributes": True}


class CandidateOutAdmin(CandidateOut):
    email: str
    created_at: datetime

    model_config = {"from_attributes": True}

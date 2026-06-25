from datetime import datetime

from pydantic import BaseModel


class ResumeCreate(BaseModel):
    title: str = "Моё резюме"
    position: str | None = None
    salary: str | None = None
    employment: str | None = None
    city: str | None = None
    education: str | None = None
    skills: str | None = None
    experience: str | None = None
    about: str | None = None
    languages: str | None = None
    driving: str | None = None
    status: str = "draft"


class ResumeUpdate(BaseModel):
    title: str | None = None
    position: str | None = None
    salary: str | None = None
    employment: str | None = None
    city: str | None = None
    education: str | None = None
    skills: str | None = None
    experience: str | None = None
    about: str | None = None
    languages: str | None = None
    driving: str | None = None
    status: str | None = None


class ResumeOut(BaseModel):
    id: int
    candidate_id: int
    title: str
    position: str | None
    salary: str | None
    employment: str | None
    city: str | None
    education: str | None
    skills: str | None
    experience: str | None
    about: str | None
    languages: str | None
    driving: str | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ResumeOutWithCandidate(ResumeOut):
    candidate_name: str | None = None
    candidate_surname: str | None = None
    candidate_phone: str | None = None

    model_config = {"from_attributes": True}

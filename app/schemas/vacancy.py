from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class VacancyStatusEnum(str, Enum):
    draft = "draft"
    published = "published"


class VacancyCreate(BaseModel):
    title: str
    description: str | None = None
    salary: str | None = None
    city: str | None = None
    education: str | None = None
    experience: str | None = None
    employment_type: str | None = None
    work_format: str | None = None
    requirements: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    status: VacancyStatusEnum | None = None


class VacancyUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    salary: str | None = None
    city: str | None = None
    education: str | None = None
    experience: str | None = None
    employment_type: str | None = None
    work_format: str | None = None
    requirements: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    status: VacancyStatusEnum | None = None


class VacancyOut(BaseModel):
    id: int
    employer_id: int
    title: str
    description: str | None
    salary: str | None
    city: str | None
    education: str | None
    experience: str | None
    employment_type: str | None
    work_format: str | None
    requirements: str | None
    contact_phone: str | None
    contact_email: str | None
    status: str
    created_at: datetime
    company_name: str | None = None
    employer_phone: str | None = None

    model_config = {"from_attributes": True}

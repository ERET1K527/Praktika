from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class StatusEnum(str, Enum):
    pending = "pending"
    reviewed = "reviewed"
    accepted = "accepted"
    rejected = "rejected"


class ApplicationCreate(BaseModel):
    vacancy_id: int


class ApplicationUpdateStatus(BaseModel):
    status: StatusEnum


class ApplicationOut(BaseModel):
    id: int
    vacancy_id: int
    candidate_id: int
    status: StatusEnum
    created_at: datetime

    model_config = {"from_attributes": True}

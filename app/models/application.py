import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.db import Base


class StatusEnum(str, enum.Enum):
    pending = "pending"
    reviewed = "reviewed"
    accepted = "accepted"
    rejected = "rejected"


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    vacancy_id: Mapped[int] = mapped_column(ForeignKey("vacancies.id"), index=True, nullable=False)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"), index=True, nullable=False)
    status: Mapped[StatusEnum] = mapped_column(Enum(StatusEnum), default=StatusEnum.pending)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    vacancy: Mapped["Vacancy"] = relationship("Vacancy", back_populates="applications")
    candidate: Mapped["Candidate"] = relationship("Candidate", back_populates="applications")
    chat: Mapped["Chat | None"] = relationship("Chat", back_populates="application", uselist=False, cascade="all, delete-orphan")

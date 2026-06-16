import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.db import Base


class RoleEnum(str, enum.Enum):
    admin = "admin"
    employer = "employer"
    candidate = "candidate"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), unique=True, index=True, nullable=True)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[RoleEnum] = mapped_column(Enum(RoleEnum), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    candidate: Mapped["Candidate | None"] = relationship(
        "Candidate", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    employer: Mapped["Employer | None"] = relationship(
        "Employer", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

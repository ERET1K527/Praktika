from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.db import Base


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    surname: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20))
    city: Mapped[str | None] = mapped_column(String(100))
    skills: Mapped[str | None] = mapped_column(Text)
    experience: Mapped[str | None] = mapped_column(Text)
    education: Mapped[str | None] = mapped_column(Text)
    resume: Mapped[str | None] = mapped_column(Text)

    user: Mapped["User"] = relationship("User", back_populates="candidate")
    applications: Mapped[list["Application"]] = relationship(
        "Application", back_populates="candidate", cascade="all, delete-orphan"
    )
    resumes: Mapped[list["Resume"]] = relationship(
        "Resume", back_populates="candidate", cascade="all, delete-orphan", order_by="Resume.id"
    )

import os
import sys
import enum
from datetime import datetime, timedelta, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI, APIRouter, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordBearer

from sqlalchemy import create_engine, select, DateTime, Enum, ForeignKey, Integer, String, Text, Boolean, func, exists
from sqlalchemy.orm import (
    DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker, Session,
)

from pydantic import BaseModel, EmailStr
from pydantic_settings import BaseSettings

import bcrypt
from jose import jwt


# ─── Settings ───

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./jobflow.db"
    REDIS_URL: str = "redis://localhost:6379/0"
    SECRET_KEY: str = "super-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# ─── Database ───

engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ─── Security ───

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user = UserRepo.get_by_id(db, int(user_id))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def require_role(*roles):
    def checker(current_user=Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        return current_user
    return checker


# ─── Models ───

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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    candidate: Mapped["Candidate | None"] = relationship("Candidate", back_populates="user", uselist=False, cascade="all, delete-orphan")
    employer: Mapped["Employer | None"] = relationship("Employer", back_populates="user", uselist=False, cascade="all, delete-orphan")


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
    applications: Mapped[list["Application"]] = relationship("Application", back_populates="candidate", cascade="all, delete-orphan")
    resumes: Mapped[list["Resume"]] = relationship("Resume", back_populates="candidate", cascade="all, delete-orphan", order_by="Resume.id")


class Employer(Base):
    __tablename__ = "employers"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True, nullable=False)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    website: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(String(20))
    verified: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped["User"] = relationship("User", back_populates="employer")
    vacancies: Mapped[list["Vacancy"]] = relationship("Vacancy", back_populates="employer", cascade="all, delete-orphan")


class VacancyStatusEnum(str, enum.Enum):
    draft = "draft"
    published = "published"


class Vacancy(Base):
    __tablename__ = "vacancies"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    employer_id: Mapped[int] = mapped_column(ForeignKey("employers.id"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    salary: Mapped[str | None] = mapped_column(String(100))
    city: Mapped[str | None] = mapped_column(String(100))
    education: Mapped[str | None] = mapped_column(String(255))
    experience: Mapped[str | None] = mapped_column(String(255))
    employment_type: Mapped[str | None] = mapped_column(String(100))
    work_format: Mapped[str | None] = mapped_column(String(100))
    requirements: Mapped[str | None] = mapped_column(Text)
    contact_phone: Mapped[str | None] = mapped_column(String(20))
    contact_email: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[VacancyStatusEnum] = mapped_column(Enum(VacancyStatusEnum), default=VacancyStatusEnum.draft)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    employer: Mapped["Employer"] = relationship("Employer", back_populates="vacancies")
    applications: Mapped[list["Application"]] = relationship("Application", back_populates="vacancy", cascade="all, delete-orphan")


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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    vacancy: Mapped["Vacancy"] = relationship("Vacancy", back_populates="applications")
    candidate: Mapped["Candidate"] = relationship("Candidate", back_populates="applications")
    chat: Mapped["Chat | None"] = relationship("Chat", back_populates="application", uselist=False, cascade="all, delete-orphan")


class Chat(Base):
    __tablename__ = "chats"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), unique=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    application: Mapped["Application"] = relationship("Application", back_populates="chat")
    messages: Mapped[list["Message"]] = relationship("Message", back_populates="chat", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id"), index=True, nullable=False)
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    chat: Mapped["Chat"] = relationship("Chat", back_populates="messages")
    sender: Mapped["User"] = relationship("User")


class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False, default="Моё резюме")
    position: Mapped[str | None] = mapped_column(String(200))
    salary: Mapped[str | None] = mapped_column(String(100))
    employment: Mapped[str | None] = mapped_column(String(100))
    city: Mapped[str | None] = mapped_column(String(100))
    education: Mapped[str | None] = mapped_column(String(200))
    skills: Mapped[str | None] = mapped_column(Text)
    experience: Mapped[str | None] = mapped_column(Text)
    about: Mapped[str | None] = mapped_column(Text)
    languages: Mapped[str | None] = mapped_column(String(300))
    driving: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    candidate: Mapped["Candidate"] = relationship("Candidate", back_populates="resumes")


# ─── Schemas ───

class AuthRoleEnum(str, enum.Enum):
    admin = "admin"
    employer = "employer"
    candidate = "candidate"


class RegisterRequest(BaseModel):
    email: EmailStr | None = None
    password: str
    role: AuthRoleEnum
    phone: str | None = None
    first_name: str | None = None
    surname: str | None = None


class LoginRequest(BaseModel):
    email: str | None = None
    password: str
    phone: str | None = None
    login_type: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    email: str | None = None
    phone: str | None = None
    role: AuthRoleEnum
    created_at: datetime
    model_config = {"from_attributes": True}


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class UpdateEmailRequest(BaseModel):
    new_email: str | None = None
    current_password: str


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


class EmployerCreate(BaseModel):
    company_name: str
    website: str | None = None
    description: str | None = None
    phone: str | None = None


class EmployerUpdate(BaseModel):
    company_name: str | None = None
    website: str | None = None
    description: str | None = None
    phone: str | None = None


class EmployerOut(BaseModel):
    id: int
    user_id: int
    company_name: str
    website: str | None
    description: str | None
    phone: str | None
    verified: bool
    model_config = {"from_attributes": True}


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
    status: VacancyStatusEnum
    created_at: datetime
    company_name: str | None = None
    employer_phone: str | None = None
    model_config = {"from_attributes": True}


class ApplicationCreate(BaseModel):
    vacancy_id: int


class ApplicationOut(BaseModel):
    id: int
    vacancy_id: int
    candidate_id: int
    status: StatusEnum
    created_at: datetime
    model_config = {"from_attributes": True}


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


# ─── Repositories ───

class UserRepo:
    @staticmethod
    def get_by_email(db: Session, email: str) -> User | None:
        return db.execute(select(User).where(User.email == email)).scalar_one_or_none()

    @staticmethod
    def get_by_phone(db: Session, phone: str) -> User | None:
        return db.execute(select(User).where(User.phone == phone)).scalar_one_or_none()

    @staticmethod
    def get_by_id(db: Session, user_id: int) -> User | None:
        return db.get(User, user_id)

    @staticmethod
    def create(db: Session, user: User) -> User:
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def get_all(db: Session, skip: int = 0, limit: int = 50) -> list[User]:
        return db.execute(select(User).offset(skip).limit(limit)).scalars().all()

    @staticmethod
    def delete(db: Session, user: User) -> None:
        db.delete(user)
        db.commit()


class CandidateRepo:
    @staticmethod
    def get_by_user_id(db: Session, user_id: int) -> Candidate | None:
        return db.execute(select(Candidate).where(Candidate.user_id == user_id)).scalar_one_or_none()

    @staticmethod
    def get_by_id(db: Session, candidate_id: int) -> Candidate | None:
        return db.get(Candidate, candidate_id)

    @staticmethod
    def create(db: Session, candidate: Candidate) -> Candidate:
        db.add(candidate)
        db.commit()
        db.refresh(candidate)
        return candidate

    @staticmethod
    def update(db: Session, candidate: Candidate, data: dict) -> Candidate:
        for key, value in data.items():
            if value is not None:
                setattr(candidate, key, value)
        db.commit()
        db.refresh(candidate)
        return candidate

    @staticmethod
    def get_all(db: Session, skip: int = 0, limit: int = 50) -> list[Candidate]:
        return db.execute(select(Candidate).offset(skip).limit(limit)).scalars().all()


class EmployerRepo:
    @staticmethod
    def get_by_user_id(db: Session, user_id: int) -> Employer | None:
        return db.execute(select(Employer).where(Employer.user_id == user_id)).scalar_one_or_none()

    @staticmethod
    def get_by_id(db: Session, employer_id: int) -> Employer | None:
        return db.get(Employer, employer_id)

    @staticmethod
    def create(db: Session, employer: Employer) -> Employer:
        db.add(employer)
        db.commit()
        db.refresh(employer)
        return employer

    @staticmethod
    def update(db: Session, employer: Employer, data: dict) -> Employer:
        for key, value in data.items():
            if value is not None:
                setattr(employer, key, value)
        db.commit()
        db.refresh(employer)
        return employer

    @staticmethod
    def get_all(db: Session, skip: int = 0, limit: int = 50) -> list[Employer]:
        return db.execute(select(Employer).offset(skip).limit(limit)).scalars().all()


class VacancyRepo:
    @staticmethod
    def get_by_id(db: Session, vacancy_id: int) -> Vacancy | None:
        return db.get(Vacancy, vacancy_id)

    @staticmethod
    def create(db: Session, vacancy: Vacancy) -> Vacancy:
        db.add(vacancy)
        db.commit()
        db.refresh(vacancy)
        return vacancy

    @staticmethod
    def update(db: Session, vacancy: Vacancy, data: dict) -> Vacancy:
        for key, value in data.items():
            if value is not None:
                setattr(vacancy, key, value)
        db.commit()
        db.refresh(vacancy)
        return vacancy

    @staticmethod
    def delete(db: Session, vacancy: Vacancy) -> None:
        db.delete(vacancy)
        db.commit()

    @staticmethod
    def get_all(db: Session, skip: int = 0, limit: int = 50, city: str | None = None) -> list[Vacancy]:
        q = select(Vacancy)
        if city:
            q = q.where(Vacancy.city.ilike(f"%{city}%"))
        return db.execute(q.offset(skip).limit(limit)).scalars().all()

    @staticmethod
    def get_published(db: Session, skip: int = 0, limit: int = 50, city: str | None = None, search: str | None = None) -> list[Vacancy]:
        q = select(Vacancy).where(Vacancy.status == VacancyStatusEnum.published)
        if city:
            q = q.where(Vacancy.city.ilike(f"%{city}%"))
        if search:
            q = q.where(Vacancy.title.ilike(f"%{search}%"))
        return db.execute(q.offset(skip).limit(limit)).scalars().all()

    @staticmethod
    def get_by_employer(db: Session, employer_id: int) -> list[Vacancy]:
        return db.execute(select(Vacancy).where(Vacancy.employer_id == employer_id)).scalars().all()


class ApplicationRepo:
    @staticmethod
    def create(db: Session, application: Application) -> Application:
        db.add(application)
        db.commit()
        db.refresh(application)
        return application

    @staticmethod
    def get_by_id(db: Session, application_id: int) -> Application | None:
        return db.get(Application, application_id)

    @staticmethod
    def update_status(db: Session, application: Application, st) -> Application:
        application.status = st
        db.commit()
        db.refresh(application)
        return application

    @staticmethod
    def get_by_candidate(db: Session, candidate_id: int) -> list[Application]:
        return db.execute(select(Application).where(Application.candidate_id == candidate_id)).scalars().all()

    @staticmethod
    def get_by_vacancy(db: Session, vacancy_id: int) -> list[Application]:
        return db.execute(select(Application).where(Application.vacancy_id == vacancy_id)).scalars().all()

    @staticmethod
    def get_all(db: Session, skip: int = 0, limit: int = 50) -> list[Application]:
        return db.execute(select(Application).offset(skip).limit(limit)).scalars().all()


class ResumeRepo:
    @staticmethod
    def create(db: Session, resume: Resume) -> Resume:
        db.add(resume)
        db.commit()
        db.refresh(resume)
        return resume

    @staticmethod
    def get_by_id(db: Session, resume_id: int) -> Resume | None:
        return db.get(Resume, resume_id)

    @staticmethod
    def get_by_candidate(db: Session, candidate_id: int) -> list[Resume]:
        return db.execute(select(Resume).where(Resume.candidate_id == candidate_id).order_by(Resume.updated_at.desc())).scalars().all()

    @staticmethod
    def update(db: Session, resume: Resume, data: dict) -> Resume:
        for key, value in data.items():
            if value is not None:
                setattr(resume, key, value)
        db.commit()
        db.refresh(resume)
        return resume

    @staticmethod
    def delete(db: Session, resume: Resume) -> None:
        db.delete(resume)
        db.commit()


class ChatRepo:
    @staticmethod
    def get_by_application(db: Session, application_id: int) -> Chat | None:
        return db.execute(select(Chat).where(Chat.application_id == application_id)).scalar_one_or_none()

    @staticmethod
    def get_by_id(db: Session, chat_id: int) -> Chat | None:
        return db.get(Chat, chat_id)

    @staticmethod
    def get_by_user(db: Session, user_id: int) -> list[Chat]:
        apps = db.execute(
            select(Application).where(
                (Application.candidate_id.in_(
                    select(Candidate.id).where(Candidate.user_id == user_id)
                )) | (Application.vacancy_id.in_(
                    select(Vacancy.id).where(Vacancy.employer_id.in_(
                        select(Employer.id).where(Employer.user_id == user_id)
                    ))
                ))
            )
        ).scalars().all()
        app_ids = [a.id for a in apps]
        if not app_ids:
            return []
        return db.execute(select(Chat).where(Chat.application_id.in_(app_ids))).scalars().all()

    @staticmethod
    def create(db: Session, chat: Chat) -> Chat:
        db.add(chat)
        db.commit()
        db.refresh(chat)
        return chat

    @staticmethod
    def get_messages(db: Session, chat_id: int) -> list[Message]:
        return db.execute(select(Message).where(Message.chat_id == chat_id).order_by(Message.created_at)).scalars().all()


class MessageRepo:
    @staticmethod
    def create(db: Session, message: Message) -> Message:
        db.add(message)
        db.commit()
        db.refresh(message)
        return message


# ─── Services ───

# Auth
def register(db: Session, data: RegisterRequest) -> TokenResponse:
    if data.email:
        existing = UserRepo.get_by_email(db, data.email)
        if existing:
            raise ValueError("Этот email уже зарегистрирован")
    if data.phone:
        existing_phone = UserRepo.get_by_phone(db, data.phone)
        if existing_phone:
            raise ValueError("Телефон уже зарегистрирован")
    if not data.email and not data.phone:
        raise ValueError("Укажите email или телефон")

    user = User(email=data.email or None, phone=data.phone or None, password=hash_password(data.password), role=data.role)
    user = UserRepo.create(db, user)

    if data.role == RoleEnum.candidate:
        CandidateRepo.create(db, Candidate(
            user_id=user.id, name=data.first_name or "", surname=data.surname or "", phone=data.phone,
        ))
    elif data.role == RoleEnum.employer:
        EmployerRepo.create(db, Employer(user_id=user.id, company_name=""))

    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return TokenResponse(access_token=token)


def login(db: Session, data: LoginRequest) -> TokenResponse:
    user = None
    if data.login_type == "phone" and data.phone:
        user = UserRepo.get_by_phone(db, data.phone)
    elif data.email:
        user = UserRepo.get_by_email(db, data.email)
    elif data.phone:
        user = UserRepo.get_by_phone(db, data.phone)

    if not user or not verify_password(data.password, user.password):
        raise ValueError("Неверный email/телефон или пароль")

    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return TokenResponse(access_token=token)


def change_password(db: Session, user: User, data: ChangePasswordRequest) -> None:
    if not verify_password(data.current_password, user.password):
        raise ValueError("Неверный текущий пароль")
    if len(data.new_password) < 8:
        raise ValueError("Новый пароль должен быть не менее 8 символов")
    user.password = hash_password(data.new_password)
    db.commit()


def update_email(db: Session, user: User, data: UpdateEmailRequest) -> None:
    if not verify_password(data.current_password, user.password):
        raise ValueError("Неверный пароль")
    if data.new_email:
        existing = UserRepo.get_by_email(db, data.new_email)
        if existing and existing.id != user.id:
            raise ValueError("Этот email уже занят")
    user.email = data.new_email or None
    db.commit()


# Candidate
def get_candidate_profile(db: Session, user_id: int) -> Candidate | None:
    return CandidateRepo.get_by_user_id(db, user_id)


def create_candidate_profile(db: Session, user_id: int, data: CandidateCreate) -> Candidate:
    candidate = CandidateRepo.get_by_user_id(db, user_id)
    if candidate is None:
        raise ValueError("Candidate profile not found")
    return CandidateRepo.update(db, candidate, data.model_dump())


def update_candidate_profile(db: Session, user_id: int, data: CandidateUpdate) -> Candidate:
    candidate = CandidateRepo.get_by_user_id(db, user_id)
    if candidate is None:
        raise ValueError("Candidate profile not found")
    return CandidateRepo.update(db, candidate, data.model_dump(exclude_unset=True))


# Employer
def get_employer_profile(db: Session, user_id: int) -> Employer | None:
    return EmployerRepo.get_by_user_id(db, user_id)


def create_employer_profile(db: Session, user_id: int, data: EmployerCreate) -> Employer:
    employer = EmployerRepo.get_by_user_id(db, user_id)
    if employer is None:
        raise ValueError("Employer profile not found")
    return EmployerRepo.update(db, employer, data.model_dump())


def update_employer_profile(db: Session, user_id: int, data: EmployerUpdate) -> Employer:
    employer = EmployerRepo.get_by_user_id(db, user_id)
    if employer is None:
        raise ValueError("Employer profile not found")
    return EmployerRepo.update(db, employer, data.model_dump(exclude_unset=True))


# Vacancy
def _enrich_vacancy(vacancy: Vacancy, db: Session) -> dict:
    employer = EmployerRepo.get_by_id(db, vacancy.employer_id)
    return {
        "id": vacancy.id, "employer_id": vacancy.employer_id, "title": vacancy.title,
        "description": vacancy.description, "salary": vacancy.salary, "city": vacancy.city,
        "education": vacancy.education, "experience": vacancy.experience,
        "employment_type": vacancy.employment_type, "work_format": vacancy.work_format,
        "requirements": vacancy.requirements, "contact_phone": vacancy.contact_phone,
        "contact_email": vacancy.contact_email, "status": vacancy.status,
        "created_at": vacancy.created_at,
        "company_name": employer.company_name if employer else None,
        "employer_phone": employer.phone if employer else None,
    }


def create_vacancy(db: Session, employer_user_id: int, data: VacancyCreate) -> Vacancy:
    employer = EmployerRepo.get_by_user_id(db, employer_user_id)
    if employer is None:
        raise ValueError("Employer profile not found")
    vacancy_data = data.model_dump()
    if data.status is None:
        vacancy_data["status"] = VacancyStatusEnum.draft
    vacancy = Vacancy(employer_id=employer.id, **vacancy_data)
    return VacancyRepo.create(db, vacancy)


def update_vacancy(db: Session, vacancy_id: int, employer_user_id: int, data: VacancyUpdate) -> Vacancy:
    vacancy = VacancyRepo.get_by_id(db, vacancy_id)
    if vacancy is None:
        raise ValueError("Vacancy not found")
    employer = EmployerRepo.get_by_user_id(db, employer_user_id)
    if employer is None or vacancy.employer_id != employer.id:
        raise ValueError("Not your vacancy")
    return VacancyRepo.update(db, vacancy, data.model_dump(exclude_unset=True))


def delete_vacancy(db: Session, vacancy_id: int, employer_user_id: int) -> None:
    vacancy = VacancyRepo.get_by_id(db, vacancy_id)
    if vacancy is None:
        raise ValueError("Vacancy not found")
    employer = EmployerRepo.get_by_user_id(db, employer_user_id)
    if employer is None or vacancy.employer_id != employer.id:
        raise ValueError("Not your vacancy")
    VacancyRepo.delete(db, vacancy)


def get_published_vacancies(db: Session, skip: int = 0, limit: int = 50, city: str | None = None, search: str | None = None):
    vacancies = VacancyRepo.get_published(db, skip, limit, city, search)
    return [_enrich_vacancy(v, db) for v in vacancies]


def get_employer_vacancies(db: Session, employer_user_id: int):
    employer = EmployerRepo.get_by_user_id(db, employer_user_id)
    if employer is None:
        raise ValueError("Employer profile not found")
    return [_enrich_vacancy(v, db) for v in VacancyRepo.get_by_employer(db, employer.id)]


def get_vacancy_detail(db: Session, vacancy_id: int) -> dict:
    vacancy = VacancyRepo.get_by_id(db, vacancy_id)
    if vacancy is None:
        raise ValueError("Vacancy not found")
    return _enrich_vacancy(vacancy, db)


def publish_vacancy(db: Session, vacancy_id: int, employer_user_id: int) -> Vacancy:
    vacancy = VacancyRepo.get_by_id(db, vacancy_id)
    if vacancy is None:
        raise ValueError("Vacancy not found")
    employer = EmployerRepo.get_by_user_id(db, employer_user_id)
    if employer is None or vacancy.employer_id != employer.id:
        raise ValueError("Not your vacancy")
    vacancy.status = VacancyStatusEnum.published
    db.commit()
    db.refresh(vacancy)
    return vacancy


def apply_to_vacancy(db: Session, candidate_user_id: int, data: ApplicationCreate) -> dict:
    candidate = CandidateRepo.get_by_user_id(db, candidate_user_id)
    if candidate is None:
        raise ValueError("Candidate profile not found")
    vacancy = VacancyRepo.get_by_id(db, data.vacancy_id)
    if vacancy is None:
        raise ValueError("Vacancy not found")
    if vacancy.status != VacancyStatusEnum.published:
        raise ValueError("Вакансия не опубликована")

    existing = db.execute(
        select(Application).where(
            Application.vacancy_id == data.vacancy_id,
            Application.candidate_id == candidate.id,
        )
    ).scalar_one_or_none()
    if existing:
        raise ValueError("Вы уже откликались на эту вакансию")

    application = Application(vacancy_id=data.vacancy_id, candidate_id=candidate.id, status=StatusEnum.pending)
    application = ApplicationRepo.create(db, application)

    employer = db.get(Employer, vacancy.employer_id)
    candidate_user = db.get(User, candidate.user_id) if candidate else None
    candidate_full = ((candidate.name or "") + " " + (candidate.surname or "")).strip()

    chat = Chat(application_id=application.id)
    db.add(chat)
    db.commit()
    db.refresh(chat)

    system_msg = Message(
        chat_id=chat.id,
        sender_id=candidate_user.id if candidate_user else candidate.user_id,
        text="На вашу вакансию «" + (vacancy.title or "") + "» откликнулся кандидат" + ((": " + candidate_full) if candidate_full else ""),
    )
    db.add(system_msg)
    db.commit()

    return {
        "id": application.id,
        "vacancy_id": application.vacancy_id,
        "candidate_id": application.candidate_id,
        "status": application.status.value,
        "created_at": application.created_at,
        "chat_id": chat.id,
    }


def get_candidate_applications(db: Session, candidate_user_id: int):
    candidate = CandidateRepo.get_by_user_id(db, candidate_user_id)
    if candidate is None:
        raise ValueError("Candidate profile not found")
    return ApplicationRepo.get_by_candidate(db, candidate.id)


def get_vacancy_applications(db: Session, vacancy_id: int):
    return ApplicationRepo.get_by_vacancy(db, vacancy_id)


def get_employer_applications(db: Session, employer_user_id: int) -> list[dict]:
    employer = EmployerRepo.get_by_user_id(db, employer_user_id)
    if employer is None:
        raise ValueError("Employer profile not found")
    vacancies = VacancyRepo.get_by_employer(db, employer.id)
    result = []
    for v in vacancies:
        apps = ApplicationRepo.get_by_vacancy(db, v.id)
        for a in apps:
            cand = db.get(Candidate, a.candidate_id)
            cand_user = db.get(User, cand.user_id) if cand else None
            full_name = ((cand.name or "") + " " + (cand.surname or "")).strip() if cand else "—"
            result.append({
                "id": a.id, "vacancy_id": a.vacancy_id, "candidate_id": a.candidate_id,
                "status": a.status.value, "created_at": a.created_at,
                "vacancy_title": v.title, "candidate_name": full_name,
                "candidate_email": cand_user.email if cand_user else None,
                "candidate_phone": cand.phone if cand else None,
                "candidate_skills": cand.skills if cand else None,
                "candidate_city": cand.city if cand else None,
            })
    return result


# Resume
def list_resumes(db: Session, user_id: int) -> list[Resume]:
    candidate = CandidateRepo.get_by_user_id(db, user_id)
    if candidate is None:
        return []
    return ResumeRepo.get_by_candidate(db, candidate.id)


def get_resume(db: Session, resume_id: int, user_id: int) -> Resume | None:
    resume = ResumeRepo.get_by_id(db, resume_id)
    if resume is None:
        return None
    candidate = CandidateRepo.get_by_user_id(db, user_id)
    if candidate is None or resume.candidate_id != candidate.id:
        return None
    return resume


def create_resume(db: Session, user_id: int, data: ResumeCreate) -> Resume:
    candidate = CandidateRepo.get_by_user_id(db, user_id)
    if candidate is None:
        raise ValueError("Сначала заполните профиль кандидата")
    resume = Resume(
        candidate_id=candidate.id, title=data.title, position=data.position,
        salary=data.salary, employment=data.employment,
        city=data.city or candidate.city,
        education=data.education or candidate.education,
        skills=data.skills or candidate.skills,
        experience=data.experience or candidate.experience,
        about=data.about, languages=data.languages, driving=data.driving, status=data.status,
    )
    return ResumeRepo.create(db, resume)


def update_resume(db: Session, resume_id: int, user_id: int, data: ResumeUpdate) -> Resume:
    resume = get_resume(db, resume_id, user_id)
    if resume is None:
        raise ValueError("Резюме не найдено")
    return ResumeRepo.update(db, resume, data.model_dump(exclude_unset=True))


def delete_resume(db: Session, resume_id: int, user_id: int) -> None:
    resume = get_resume(db, resume_id, user_id)
    if resume is None:
        raise ValueError("Резюме не найдено")
    ResumeRepo.delete(db, resume)


def publish_resume(db: Session, resume_id: int, user_id: int) -> Resume:
    resume = get_resume(db, resume_id, user_id)
    if resume is None:
        raise ValueError("Резюме не найдено")
    return ResumeRepo.update(db, resume, {"status": "published"})


# Chat
def get_or_create_chat(db: Session, application_id: int, user_id: int) -> Chat:
    application = ApplicationRepo.get_by_id(db, application_id)
    if application is None:
        raise ValueError("Отклик не найден")
    candidate = db.get(Candidate, application.candidate_id)
    vacancy = db.get(Vacancy, application.vacancy_id)
    employer = db.get(Employer, vacancy.employer_id) if vacancy else None
    is_participant = False
    if candidate and candidate.user_id == user_id:
        is_participant = True
    if employer and employer.user_id == user_id:
        is_participant = True
    if not is_participant:
        raise ValueError("Нет доступа к этому чату")
    chat = ChatRepo.get_by_application(db, application_id)
    if chat is None:
        chat = Chat(application_id=application_id)
        chat = ChatRepo.create(db, chat)
    return chat


def send_message(db: Session, chat_id: int, user_id: int, data: MessageCreate) -> MessageOut:
    chat = ChatRepo.get_by_id(db, chat_id)
    if chat is None:
        raise ValueError("Чат не найден")
    application = ApplicationRepo.get_by_id(db, chat.application_id)
    if application is None:
        raise ValueError("Отклик не найден")
    candidate = db.get(Candidate, application.candidate_id)
    vacancy = db.get(Vacancy, application.vacancy_id)
    employer = db.get(Employer, vacancy.employer_id) if vacancy else None
    is_participant = False
    if candidate and candidate.user_id == user_id:
        is_participant = True
    if employer and employer.user_id == user_id:
        is_participant = True
    if not is_participant:
        raise ValueError("Нет доступа к этому чату")
    message = Message(chat_id=chat_id, sender_id=user_id, text=data.text)
    message = MessageRepo.create(db, message)
    sender = db.get(User, user_id)
    return MessageOut(
        id=message.id, chat_id=message.chat_id, sender_id=message.sender_id,
        text=message.text, created_at=message.created_at,
        sender_email=sender.email if sender else None,
    )


def get_chat_messages(db: Session, chat_id: int, user_id: int) -> list[MessageOut]:
    chat = ChatRepo.get_by_id(db, chat_id)
    if chat is None:
        raise ValueError("Чат не найден")
    application = ApplicationRepo.get_by_id(db, chat.application_id)
    if application is None:
        raise ValueError("Отклик не найден")
    candidate = db.get(Candidate, application.candidate_id)
    vacancy = db.get(Vacancy, application.vacancy_id)
    employer = db.get(Employer, vacancy.employer_id) if vacancy else None
    is_participant = False
    if candidate and candidate.user_id == user_id:
        is_participant = True
    if employer and employer.user_id == user_id:
        is_participant = True
    if not is_participant:
        raise ValueError("Нет доступа к этому чату")
    messages = ChatRepo.get_messages(db, chat_id)
    result = []
    for m in messages:
        sender = db.get(User, m.sender_id)
        result.append(MessageOut(
            id=m.id, chat_id=m.chat_id, sender_id=m.sender_id,
            text=m.text, created_at=m.created_at,
            sender_email=sender.email if sender else None,
        ))
    return result


def get_user_chats(db: Session, user_id: int) -> list[ChatOut]:
    chats = ChatRepo.get_by_user(db, user_id)
    result = []
    for chat in chats:
        application = ApplicationRepo.get_by_id(db, chat.application_id)
        if application is None:
            continue
        vacancy = db.get(Vacancy, application.vacancy_id)
        candidate = db.get(Candidate, application.candidate_id)
        candidate_user = db.get(User, candidate.user_id) if candidate else None
        employer = None
        employer_user = None
        if vacancy:
            employer = db.get(Employer, vacancy.employer_id)
            if employer:
                employer_user = db.get(User, employer.user_id)
        other_email = None
        if candidate and candidate.user_id == user_id:
            other_email = employer_user.email if employer_user else None
        elif employer and employer.user_id == user_id:
            other_email = candidate_user.email if candidate_user else None
        messages = ChatRepo.get_messages(db, chat.id)
        last_msg = messages[-1].text[:80] if messages else None
        result.append(ChatOut(
            id=chat.id, application_id=chat.application_id, created_at=chat.created_at,
            vacancy_title=vacancy.title if vacancy else None,
            other_user_email=other_email, last_message=last_msg,
        ))
    return result


# Admin
def get_dashboard(db: Session):
    return {
        "total_users": len(UserRepo.get_all(db, 0, 10000)),
        "total_candidates": len(CandidateRepo.get_all(db, 0, 10000)),
        "total_employers": len(EmployerRepo.get_all(db, 0, 10000)),
        "total_vacancies": len(VacancyRepo.get_all(db, 0, 10000)),
        "total_applications": len(ApplicationRepo.get_all(db, 0, 10000)),
    }


def list_users(db: Session, skip: int = 0, limit: int = 50):
    return UserRepo.get_all(db, skip, limit)


def list_candidates(db: Session, skip: int = 0, limit: int = 50):
    candidates = CandidateRepo.get_all(db, skip, limit)
    result = []
    for c in candidates:
        result.append({
            "id": c.id, "user_id": c.user_id, "name": c.name, "surname": c.surname,
            "phone": c.phone, "city": c.city, "skills": c.skills,
            "experience": c.experience, "education": c.education, "resume": c.resume,
            "email": c.user.email, "created_at": c.user.created_at,
        })
    return result


def list_employers(db: Session, skip: int = 0, limit: int = 50):
    return EmployerRepo.get_all(db, skip, limit)


def list_vacancies(db: Session, skip: int = 0, limit: int = 50):
    return VacancyRepo.get_all(db, skip, limit)


def list_applications(db: Session, skip: int = 0, limit: int = 50):
    return ApplicationRepo.get_all(db, skip, limit)


def delete_user(db: Session, user_id: int):
    user = UserRepo.get_by_id(db, user_id)
    if user is None:
        raise ValueError("User not found")
    UserRepo.delete(db, user)


def verify_employer(db: Session, employer_id: int):
    employer = EmployerRepo.get_by_id(db, employer_id)
    if employer is None:
        raise ValueError("Employer not found")
    employer.verified = True
    db.commit()
    db.refresh(employer)
    return employer


# ─── API Routers ───

auth_router = APIRouter(prefix="/auth", tags=["Auth"])


@auth_router.post("/register", response_model=TokenResponse)
def api_register(data: RegisterRequest, db: Session = Depends(get_db)):
    try:
        return register(db, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@auth_router.post("/login", response_model=TokenResponse)
def api_login(data: LoginRequest, db: Session = Depends(get_db)):
    if not data.email and not data.phone:
        raise HTTPException(status_code=400, detail="Укажите email или телефон")
    try:
        return login(db, data)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@auth_router.get("/me", response_model=UserOut)
def api_me(current_user: User = Depends(get_current_user)):
    return current_user


@auth_router.post("/change-password")
def api_change_password(data: ChangePasswordRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        change_password(db, current_user, data)
        return {"detail": "Пароль успешно изменён"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@auth_router.post("/update-email")
def api_update_email(data: UpdateEmailRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        update_email(db, current_user, data)
        return {"detail": "Email успешно изменён"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


users_router = APIRouter(prefix="/users", tags=["Users"])


@users_router.get("/candidate/profile", response_model=CandidateOut)
def api_get_candidate_profile(current_user: User = Depends(require_role(RoleEnum.candidate)), db: Session = Depends(get_db)):
    profile = get_candidate_profile(db, current_user.id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@users_router.post("/candidate/profile", response_model=CandidateOut)
def api_create_candidate_profile(data: CandidateCreate, current_user: User = Depends(require_role(RoleEnum.candidate)), db: Session = Depends(get_db)):
    try:
        return create_candidate_profile(db, current_user.id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@users_router.put("/candidate/profile", response_model=CandidateOut)
def api_update_candidate_profile(data: CandidateUpdate, current_user: User = Depends(require_role(RoleEnum.candidate)), db: Session = Depends(get_db)):
    try:
        return update_candidate_profile(db, current_user.id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@users_router.get("/employer/profile", response_model=EmployerOut)
def api_get_employer_profile(current_user: User = Depends(require_role(RoleEnum.employer)), db: Session = Depends(get_db)):
    profile = get_employer_profile(db, current_user.id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@users_router.post("/employer/profile", response_model=EmployerOut)
def api_create_employer_profile(data: EmployerCreate, current_user: User = Depends(require_role(RoleEnum.employer)), db: Session = Depends(get_db)):
    try:
        return create_employer_profile(db, current_user.id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@users_router.put("/employer/profile", response_model=EmployerOut)
def api_update_employer_profile(data: EmployerUpdate, current_user: User = Depends(require_role(RoleEnum.employer)), db: Session = Depends(get_db)):
    try:
        return update_employer_profile(db, current_user.id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


admin_router = APIRouter(prefix="/admin", tags=["Admin"])


@admin_router.get("/dashboard")
def api_dashboard(current_user: User = Depends(require_role(RoleEnum.admin)), db: Session = Depends(get_db)):
    return get_dashboard(db)


@admin_router.get("/users", response_model=list[UserOut])
def api_list_users(skip: int = 0, limit: int = 50, current_user: User = Depends(require_role(RoleEnum.admin)), db: Session = Depends(get_db)):
    return list_users(db, skip, limit)


@admin_router.get("/candidates")
def api_list_candidates(skip: int = 0, limit: int = 50, current_user: User = Depends(require_role(RoleEnum.admin)), db: Session = Depends(get_db)):
    return list_candidates(db, skip, limit)


@admin_router.get("/employers", response_model=list[EmployerOut])
def api_list_employers(skip: int = 0, limit: int = 50, current_user: User = Depends(require_role(RoleEnum.admin)), db: Session = Depends(get_db)):
    return list_employers(db, skip, limit)


@admin_router.get("/vacancies", response_model=list[VacancyOut])
def api_list_vacancies(skip: int = 0, limit: int = 50, current_user: User = Depends(require_role(RoleEnum.admin)), db: Session = Depends(get_db)):
    return list_vacancies(db, skip, limit)


@admin_router.get("/applications", response_model=list[ApplicationOut])
def api_list_applications(skip: int = 0, limit: int = 50, current_user: User = Depends(require_role(RoleEnum.admin)), db: Session = Depends(get_db)):
    return list_applications(db, skip, limit)


@admin_router.delete("/users/{user_id}")
def api_delete_user(user_id: int, current_user: User = Depends(require_role(RoleEnum.admin)), db: Session = Depends(get_db)):
    try:
        delete_user(db, user_id)
        return {"detail": "User deleted"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@admin_router.post("/employers/{employer_id}/verify", response_model=EmployerOut)
def api_verify_employer(employer_id: int, current_user: User = Depends(require_role(RoleEnum.admin)), db: Session = Depends(get_db)):
    try:
        return verify_employer(db, employer_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


vacancies_router = APIRouter(prefix="/vacancies", tags=["Vacancies"])


@vacancies_router.get("/", response_model=list[VacancyOut])
def api_list_vacancies(skip: int = 0, limit: int = 50, city: str | None = None, search: str | None = None, db: Session = Depends(get_db)):
    return get_published_vacancies(db, skip, limit, city, search)


@vacancies_router.get("/{vacancy_id}", response_model=VacancyOut)
def api_get_vacancy(vacancy_id: int, db: Session = Depends(get_db)):
    try:
        return get_vacancy_detail(db, vacancy_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@vacancies_router.post("/", response_model=VacancyOut)
def api_create_vacancy(data: VacancyCreate, current_user: User = Depends(require_role(RoleEnum.employer)), db: Session = Depends(get_db)):
    try:
        return create_vacancy(db, current_user.id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@vacancies_router.get("/my", response_model=list[VacancyOut])
def api_my_vacancies(current_user: User = Depends(require_role(RoleEnum.employer)), db: Session = Depends(get_db)):
    try:
        return get_employer_vacancies(db, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@vacancies_router.post("/{vacancy_id}/publish", response_model=VacancyOut)
def api_publish_vacancy(vacancy_id: int, current_user: User = Depends(require_role(RoleEnum.employer)), db: Session = Depends(get_db)):
    try:
        return publish_vacancy(db, vacancy_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@vacancies_router.put("/{vacancy_id}", response_model=VacancyOut)
def api_update_vacancy(vacancy_id: int, data: VacancyUpdate, current_user: User = Depends(require_role(RoleEnum.employer)), db: Session = Depends(get_db)):
    try:
        return update_vacancy(db, vacancy_id, current_user.id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@vacancies_router.delete("/{vacancy_id}")
def api_delete_vacancy(vacancy_id: int, current_user: User = Depends(require_role(RoleEnum.employer)), db: Session = Depends(get_db)):
    try:
        delete_vacancy(db, vacancy_id, current_user.id)
        return {"detail": "Vacancy deleted"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@vacancies_router.post("/{vacancy_id}/apply")
def api_apply_to_vacancy(vacancy_id: int, current_user: User = Depends(require_role(RoleEnum.candidate)), db: Session = Depends(get_db)):
    try:
        data = ApplicationCreate(vacancy_id=vacancy_id)
        return apply_to_vacancy(db, current_user.id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@vacancies_router.get("/{vacancy_id}/applications", response_model=list[ApplicationOut])
def api_vacancy_applications(vacancy_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_vacancy_applications(db, vacancy_id)


@vacancies_router.get("/my/applications", response_model=list[ApplicationOut])
def api_my_applications(current_user: User = Depends(require_role(RoleEnum.candidate)), db: Session = Depends(get_db)):
    try:
        return get_candidate_applications(db, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@vacancies_router.get("/employer/applications")
def api_employer_applications(current_user: User = Depends(require_role(RoleEnum.employer)), db: Session = Depends(get_db)):
    try:
        return get_employer_applications(db, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


chat_router = APIRouter(prefix="/chat", tags=["Chat"])


@chat_router.get("/chats", response_model=list[ChatOut])
def api_get_chats(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_user_chats(db, current_user.id)


@chat_router.post("/application/{application_id}", response_model=ChatOut)
def api_create_chat(application_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        chat = get_or_create_chat(db, application_id, current_user.id)
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
            id=chat.id, application_id=chat.application_id, created_at=chat.created_at,
            vacancy_title=vacancy.title if vacancy else None,
            other_user_email=other_email, last_message=None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@chat_router.get("/{chat_id}/messages", response_model=list[MessageOut])
def api_get_messages(chat_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        return get_chat_messages(db, chat_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@chat_router.post("/{chat_id}/messages", response_model=MessageOut)
def api_send_message(chat_id: int, data: MessageCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        return send_message(db, chat_id, current_user.id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


resumes_router = APIRouter(prefix="/resumes", tags=["Resumes"])


@resumes_router.get("/", response_model=list[ResumeOut])
def api_list_resumes(current_user: User = Depends(require_role(RoleEnum.candidate)), db: Session = Depends(get_db)):
    return list_resumes(db, current_user.id)


@resumes_router.post("/", response_model=ResumeOut)
def api_create_resume(data: ResumeCreate, current_user: User = Depends(require_role(RoleEnum.candidate)), db: Session = Depends(get_db)):
    try:
        return create_resume(db, current_user.id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@resumes_router.get("/{resume_id}", response_model=ResumeOut)
def api_get_resume(resume_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role == RoleEnum.candidate:
        resume = get_resume(db, resume_id, current_user.id)
        if resume is None:
            raise HTTPException(status_code=404, detail="Резюме не найдено")
        return resume
    elif current_user.role in (RoleEnum.employer, RoleEnum.admin):
        resume = ResumeRepo.get_by_id(db, resume_id)
        if resume is None:
            raise HTTPException(status_code=404, detail="Резюме не найдено")
        return resume
    raise HTTPException(status_code=403, detail="Нет доступа")


@resumes_router.get("/candidate/{candidate_id}", response_model=list[ResumeOut])
def api_list_candidate_resumes(candidate_id: int, current_user: User = Depends(require_role(RoleEnum.employer, RoleEnum.admin)), db: Session = Depends(get_db)):
    candidate = CandidateRepo.get_by_id(db, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Кандидат не найден")
    return ResumeRepo.get_by_candidate(db, candidate.id)


@resumes_router.put("/{resume_id}", response_model=ResumeOut)
def api_update_resume(resume_id: int, data: ResumeUpdate, current_user: User = Depends(require_role(RoleEnum.candidate)), db: Session = Depends(get_db)):
    try:
        return update_resume(db, resume_id, current_user.id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@resumes_router.delete("/{resume_id}")
def api_delete_resume(resume_id: int, current_user: User = Depends(require_role(RoleEnum.candidate)), db: Session = Depends(get_db)):
    try:
        delete_resume(db, resume_id, current_user.id)
        return {"detail": "Резюме удалено"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@resumes_router.post("/{resume_id}/publish", response_model=ResumeOut)
def api_publish_resume(resume_id: int, current_user: User = Depends(require_role(RoleEnum.candidate)), db: Session = Depends(get_db)):
    try:
        return publish_resume(db, resume_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ─── App ───

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _create_admin()
    yield


def _create_admin():
    db = Session(bind=engine)
    try:
        existing = db.query(User).filter(User.email == "admin@jobflow.ru").first()
        if not existing:
            admin = User(
                email="admin@jobflow.ru",
                password=hash_password("admin123"),
                role=RoleEnum.admin,
            )
            db.add(admin)
            db.commit()
    finally:
        db.close()


app = FastAPI(title="JobFlow API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(vacancies_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(resumes_router, prefix="/api")

app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "app", "static")), name="static")


@app.get("/")
def serve_index():
    return FileResponse(os.path.join(BASE_DIR, "index.html"))


@app.get("/{name}.html")
def serve_page(name: str):
    return FileResponse(os.path.join(BASE_DIR, f"{name}.html"))


@app.get("/css/{name}.css")
def serve_css(name: str):
    return FileResponse(os.path.join(BASE_DIR, "css", f"{name}.css"))


@app.get("/{name}.js")
def serve_js(name: str):
    return FileResponse(os.path.join(BASE_DIR, f"{name}.js"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)

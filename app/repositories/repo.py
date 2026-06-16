from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.candidate import Candidate
from app.models.employer import Employer
from app.models.vacancy import Vacancy, VacancyStatusEnum
from app.models.application import Application
from app.models.resume import Resume


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
    def update_status(db: Session, application: Application, status) -> Application:
        application.status = status
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
    def get_published(db: Session, skip: int = 0, limit: int = 50, city: str | None = None, search: str | None = None, position: str | None = None) -> list[Resume]:
        q = select(Resume).where(Resume.status == "published")
        if city:
            q = q.where(Resume.city.ilike(f"%{city}%"))
        if search:
            q = q.where(Resume.title.ilike(f"%{search}%"))
        if position:
            q = q.where(Resume.position.ilike(f"%{position}%"))
        return db.execute(q.order_by(Resume.updated_at.desc()).offset(skip).limit(limit)).scalars().all()

    @staticmethod
    def delete(db: Session, resume: Resume) -> None:
        db.delete(resume)
        db.commit()

from sqlalchemy.orm import Session

from app.models import Resume
from app.repositories.repo import ResumeRepo, CandidateRepo
from app.schemas.resume import ResumeCreate, ResumeUpdate


def list_resumes(db: Session, user_id: int) -> list[Resume]:
    candidate = CandidateRepo.get_by_user_id(db, user_id)
    if candidate is None:
        return []
    return ResumeRepo.get_by_candidate(db, candidate.id)


def browse_published_resumes(db: Session, skip: int = 0, limit: int = 50, city: str | None = None, search: str | None = None, position: str | None = None) -> list[Resume]:
    return ResumeRepo.get_published(db, skip, limit, city, search, position)


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
        candidate_id=candidate.id,
        title=data.title,
        position=data.position,
        salary=data.salary,
        employment=data.employment,
        city=data.city or candidate.city,
        education=data.education or candidate.education,
        skills=data.skills or candidate.skills,
        experience=data.experience or candidate.experience,
        about=data.about,
        languages=data.languages,
        driving=data.driving,
        status=data.status,
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

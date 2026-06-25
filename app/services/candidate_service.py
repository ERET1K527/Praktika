from sqlalchemy.orm import Session

from app.models import Candidate
from app.repositories.repo import CandidateRepo
from app.schemas.candidate import CandidateCreate, CandidateUpdate


def get_my_profile(db: Session, user_id: int) -> Candidate | None:
    return CandidateRepo.get_by_user_id(db, user_id)


def create_profile(db: Session, user_id: int, data: CandidateCreate) -> Candidate:
    candidate = CandidateRepo.get_by_user_id(db, user_id)
    if candidate is None:
        raise ValueError("Candidate profile not found")
    return CandidateRepo.update(db, candidate, data.model_dump())


def update_profile(db: Session, user_id: int, data: CandidateUpdate) -> Candidate:
    candidate = CandidateRepo.get_by_user_id(db, user_id)
    if candidate is None:
        raise ValueError("Candidate profile not found")
    return CandidateRepo.update(db, candidate, data.model_dump(exclude_unset=True))


def get_all_candidates(db: Session, skip: int = 0, limit: int = 50):
    return CandidateRepo.get_all(db, skip, limit)

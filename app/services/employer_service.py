from sqlalchemy.orm import Session

from app.models import Employer
from app.repositories.repo import EmployerRepo
from app.schemas.employer import EmployerCreate, EmployerUpdate


def get_my_profile(db: Session, user_id: int) -> Employer | None:
    return EmployerRepo.get_by_user_id(db, user_id)


def create_profile(db: Session, user_id: int, data: EmployerCreate) -> Employer:
    employer = EmployerRepo.get_by_user_id(db, user_id)
    if employer is None:
        raise ValueError("Employer profile not found")
    return EmployerRepo.update(db, employer, data.model_dump())


def update_profile(db: Session, user_id: int, data: EmployerUpdate) -> Employer:
    employer = EmployerRepo.get_by_user_id(db, user_id)
    if employer is None:
        raise ValueError("Employer profile not found")
    return EmployerRepo.update(db, employer, data.model_dump(exclude_unset=True))


def get_all_employers(db: Session, skip: int = 0, limit: int = 50):
    return EmployerRepo.get_all(db, skip, limit)

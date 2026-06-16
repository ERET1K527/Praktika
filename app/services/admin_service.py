from sqlalchemy.orm import Session

from app.repositories.repo import UserRepo, CandidateRepo, EmployerRepo, VacancyRepo, ApplicationRepo
from app.models import RoleEnum


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
            "id": c.id,
            "user_id": c.user_id,
            "name": c.name,
            "surname": c.surname,
            "phone": c.phone,
            "city": c.city,
            "skills": c.skills,
            "experience": c.experience,
            "education": c.education,
            "resume": c.resume,
            "email": c.user.email,
            "created_at": c.user.created_at,
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

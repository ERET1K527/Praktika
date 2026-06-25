from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.core.deps import require_role
from app.models import User, RoleEnum
from app.schemas.auth import UserOut
from app.schemas.employer import EmployerOut
from app.schemas.vacancy import VacancyOut
from app.schemas.application import ApplicationOut
from app.services.admin_service import (
    get_dashboard, list_users, list_candidates, list_employers,
    list_vacancies, list_applications, delete_user, verify_employer,
)

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/dashboard")
def api_dashboard(current_user: User = Depends(require_role(RoleEnum.admin)), db: Session = Depends(get_db)):
    return get_dashboard(db)


@router.get("/users", response_model=list[UserOut])
def api_list_users(skip: int = 0, limit: int = 50, current_user: User = Depends(require_role(RoleEnum.admin)), db: Session = Depends(get_db)):
    return list_users(db, skip, limit)


@router.get("/candidates")
def api_list_candidates(skip: int = 0, limit: int = 50, current_user: User = Depends(require_role(RoleEnum.admin)), db: Session = Depends(get_db)):
    return list_candidates(db, skip, limit)


@router.get("/employers", response_model=list[EmployerOut])
def api_list_employers(skip: int = 0, limit: int = 50, current_user: User = Depends(require_role(RoleEnum.admin)), db: Session = Depends(get_db)):
    return list_employers(db, skip, limit)


@router.get("/vacancies", response_model=list[VacancyOut])
def api_list_vacancies(skip: int = 0, limit: int = 50, current_user: User = Depends(require_role(RoleEnum.admin)), db: Session = Depends(get_db)):
    return list_vacancies(db, skip, limit)


@router.get("/applications", response_model=list[ApplicationOut])
def api_list_applications(skip: int = 0, limit: int = 50, current_user: User = Depends(require_role(RoleEnum.admin)), db: Session = Depends(get_db)):
    return list_applications(db, skip, limit)


@router.delete("/users/{user_id}")
def api_delete_user(user_id: int, current_user: User = Depends(require_role(RoleEnum.admin)), db: Session = Depends(get_db)):
    try:
        delete_user(db, user_id)
        return {"detail": "User deleted"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/employers/{employer_id}/verify", response_model=EmployerOut)
def api_verify_employer(employer_id: int, current_user: User = Depends(require_role(RoleEnum.admin)), db: Session = Depends(get_db)):
    try:
        return verify_employer(db, employer_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

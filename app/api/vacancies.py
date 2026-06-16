from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.core.deps import get_current_user, require_role
from app.models import User, RoleEnum, VacancyStatusEnum
from app.schemas.vacancy import VacancyCreate, VacancyUpdate, VacancyOut
from app.schemas.application import ApplicationCreate, ApplicationOut
from app.services import vacancy_service

router = APIRouter(prefix="/vacancies", tags=["Vacancies"])


@router.get("/", response_model=list[VacancyOut])
def api_list_vacancies(skip: int = 0, limit: int = 50, city: str | None = None, search: str | None = None, db: Session = Depends(get_db)):
    return vacancy_service.get_published_vacancies(db, skip, limit, city, search)


@router.get("/my", response_model=list[VacancyOut])
def api_my_vacancies(current_user: User = Depends(require_role(RoleEnum.employer)), db: Session = Depends(get_db)):
    try:
        return vacancy_service.get_employer_vacancies(db, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/my/applications", response_model=list[ApplicationOut])
def api_my_applications(current_user: User = Depends(require_role(RoleEnum.candidate)), db: Session = Depends(get_db)):
    try:
        return vacancy_service.get_candidate_applications(db, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/employer/applications")
def api_employer_applications(current_user: User = Depends(require_role(RoleEnum.employer)), db: Session = Depends(get_db)):
    try:
        return vacancy_service.get_employer_applications(db, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/", response_model=VacancyOut)
def api_create_vacancy(data: VacancyCreate, current_user: User = Depends(require_role(RoleEnum.employer)), db: Session = Depends(get_db)):
    try:
        return vacancy_service.create_vacancy(db, current_user.id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{vacancy_id}", response_model=VacancyOut)
def api_get_vacancy(vacancy_id: int, db: Session = Depends(get_db)):
    try:
        return vacancy_service.get_vacancy_detail(db, vacancy_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{vacancy_id}/publish", response_model=VacancyOut)
def api_publish_vacancy(vacancy_id: int, current_user: User = Depends(require_role(RoleEnum.employer)), db: Session = Depends(get_db)):
    try:
        return vacancy_service.publish_vacancy(db, vacancy_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{vacancy_id}", response_model=VacancyOut)
def api_update_vacancy(vacancy_id: int, data: VacancyUpdate, current_user: User = Depends(require_role(RoleEnum.employer)), db: Session = Depends(get_db)):
    try:
        return vacancy_service.update_vacancy(db, vacancy_id, current_user.id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{vacancy_id}")
def api_delete_vacancy(vacancy_id: int, current_user: User = Depends(require_role(RoleEnum.employer)), db: Session = Depends(get_db)):
    try:
        vacancy_service.delete_vacancy(db, vacancy_id, current_user.id)
        return {"detail": "Vacancy deleted"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{vacancy_id}/apply")
def api_apply_to_vacancy(vacancy_id: int, current_user: User = Depends(require_role(RoleEnum.candidate)), db: Session = Depends(get_db)):
    try:
        data = ApplicationCreate(vacancy_id=vacancy_id)
        return vacancy_service.apply_to_vacancy(db, current_user.id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{vacancy_id}/applications", response_model=list[ApplicationOut])
def api_vacancy_applications(vacancy_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return vacancy_service.get_vacancy_applications(db, vacancy_id)

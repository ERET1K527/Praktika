from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.core.deps import get_current_user, require_role
from app.models import User, RoleEnum
from app.schemas.candidate import CandidateCreate, CandidateUpdate, CandidateOut
from app.schemas.employer import EmployerCreate, EmployerUpdate, EmployerOut
from app.services.candidate_service import get_my_profile as get_candidate_profile, create_profile as create_candidate_profile, update_profile as update_candidate_profile
from app.services.employer_service import get_my_profile as get_employer_profile, create_profile as create_employer_profile, update_profile as update_employer_profile

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/candidate/profile", response_model=CandidateOut)
def api_get_candidate_profile(current_user: User = Depends(require_role(RoleEnum.candidate)), db: Session = Depends(get_db)):
    profile = get_candidate_profile(db, current_user.id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.post("/candidate/profile", response_model=CandidateOut)
def api_create_candidate_profile(data: CandidateCreate, current_user: User = Depends(require_role(RoleEnum.candidate)), db: Session = Depends(get_db)):
    try:
        return create_candidate_profile(db, current_user.id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/candidate/profile", response_model=CandidateOut)
def api_update_candidate_profile(data: CandidateUpdate, current_user: User = Depends(require_role(RoleEnum.candidate)), db: Session = Depends(get_db)):
    try:
        return update_candidate_profile(db, current_user.id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/employer/profile", response_model=EmployerOut)
def api_get_employer_profile(current_user: User = Depends(require_role(RoleEnum.employer)), db: Session = Depends(get_db)):
    profile = get_employer_profile(db, current_user.id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.post("/employer/profile", response_model=EmployerOut)
def api_create_employer_profile(data: EmployerCreate, current_user: User = Depends(require_role(RoleEnum.employer)), db: Session = Depends(get_db)):
    try:
        return create_employer_profile(db, current_user.id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/employer/profile", response_model=EmployerOut)
def api_update_employer_profile(data: EmployerUpdate, current_user: User = Depends(require_role(RoleEnum.employer)), db: Session = Depends(get_db)):
    try:
        return update_employer_profile(db, current_user.id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

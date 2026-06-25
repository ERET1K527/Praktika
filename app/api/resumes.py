from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.core.deps import require_role, get_current_user
from app.models import User, RoleEnum, Candidate
from app.schemas.resume import ResumeCreate, ResumeUpdate, ResumeOut, ResumeOutWithCandidate
from app.services.resume_service import list_resumes, get_resume, create_resume, update_resume, delete_resume, publish_resume, browse_published_resumes
from app.repositories.repo import CandidateRepo

router = APIRouter(prefix="/resumes", tags=["Resumes"])


@router.get("/", response_model=list[ResumeOut])
def api_list_resumes(current_user: User = Depends(require_role(RoleEnum.candidate)), db: Session = Depends(get_db)):
    return list_resumes(db, current_user.id)


@router.post("/", response_model=ResumeOut)
def api_create_resume(data: ResumeCreate, current_user: User = Depends(require_role(RoleEnum.candidate)), db: Session = Depends(get_db)):
    try:
        return create_resume(db, current_user.id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/browse", response_model=list[ResumeOutWithCandidate])
def api_browse_resumes(skip: int = 0, limit: int = 50, city: str | None = None, search: str | None = None, position: str | None = None, current_user: User = Depends(require_role(RoleEnum.employer, RoleEnum.admin)), db: Session = Depends(get_db)):
    resumes = browse_published_resumes(db, skip, limit, city, search, position)
    result = []
    for r in resumes:
        candidate = CandidateRepo.get_by_id(db, r.candidate_id)
        rd = ResumeOutWithCandidate.model_validate(r)
        if candidate:
            rd.candidate_name = candidate.name
            rd.candidate_surname = candidate.surname
            rd.candidate_phone = candidate.phone
        result.append(rd)
    return result


@router.get("/{resume_id}", response_model=ResumeOut)
def api_get_resume(resume_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role == RoleEnum.candidate:
        resume = get_resume(db, resume_id, current_user.id)
        if resume is None:
            raise HTTPException(status_code=404, detail="Резюме не найдено")
        return resume
    elif current_user.role in (RoleEnum.employer, RoleEnum.admin):
        from app.repositories.repo import ResumeRepo
        resume = ResumeRepo.get_by_id(db, resume_id)
        if resume is None:
            raise HTTPException(status_code=404, detail="Резюме не найдено")
        return resume
    raise HTTPException(status_code=403, detail="Нет доступа")


@router.get("/candidate/{candidate_id}", response_model=list[ResumeOut])
def api_list_candidate_resumes(candidate_id: int, current_user: User = Depends(require_role(RoleEnum.employer, RoleEnum.admin)), db: Session = Depends(get_db)):
    from app.repositories.repo import ResumeRepo
    candidate = CandidateRepo.get_by_id(db, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Кандидат не найден")
    return ResumeRepo.get_by_candidate(db, candidate.id)


@router.put("/{resume_id}", response_model=ResumeOut)
def api_update_resume(resume_id: int, data: ResumeUpdate, current_user: User = Depends(require_role(RoleEnum.candidate)), db: Session = Depends(get_db)):
    try:
        return update_resume(db, resume_id, current_user.id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{resume_id}")
def api_delete_resume(resume_id: int, current_user: User = Depends(require_role(RoleEnum.candidate)), db: Session = Depends(get_db)):
    try:
        delete_resume(db, resume_id, current_user.id)
        return {"detail": "Резюме удалено"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{resume_id}/publish", response_model=ResumeOut)
def api_publish_resume(resume_id: int, current_user: User = Depends(require_role(RoleEnum.candidate)), db: Session = Depends(get_db)):
    try:
        return publish_resume(db, resume_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

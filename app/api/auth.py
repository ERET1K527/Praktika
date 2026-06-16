from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, UserOut, ChangePasswordRequest, UpdateEmailRequest
from app.services.auth_service import register, login, change_password, update_email
from app.core.deps import get_current_user
from app.models import User

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=TokenResponse)
def api_register(data: RegisterRequest, db: Session = Depends(get_db)):
    try:
        return register(db, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login", response_model=TokenResponse)
def api_login(data: LoginRequest, db: Session = Depends(get_db)):
    if not data.email and not data.phone:
        raise HTTPException(status_code=400, detail="Укажите email или телефон")
    try:
        return login(db, data)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.get("/me", response_model=UserOut)
def api_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/change-password")
def api_change_password(data: ChangePasswordRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        change_password(db, current_user, data)
        return {"detail": "Пароль успешно изменён"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/update-email")
def api_update_email(data: UpdateEmailRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        update_email(db, current_user, data)
        return {"detail": "Email успешно изменён"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

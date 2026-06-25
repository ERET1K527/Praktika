from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password, create_access_token
from app.models import User, RoleEnum, Candidate, Employer
from app.repositories.repo import UserRepo, CandidateRepo, EmployerRepo
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, ChangePasswordRequest, UpdateEmailRequest


def register(db: Session, data: RegisterRequest) -> TokenResponse:
    if data.email:
        existing = UserRepo.get_by_email(db, data.email)
        if existing:
            raise ValueError("Этот email уже зарегистрирован")
    if data.phone:
        existing_phone = UserRepo.get_by_phone(db, data.phone)
        if existing_phone:
            raise ValueError("Телефон уже зарегистрирован")
    if not data.email and not data.phone:
        raise ValueError("Укажите email или телефон")

    user = User(
        email=data.email or None,
        phone=data.phone or None,
        password=hash_password(data.password),
        role=data.role,
    )
    user = UserRepo.create(db, user)

    if data.role == RoleEnum.candidate:
        CandidateRepo.create(db, Candidate(
            user_id=user.id,
            name=data.first_name or "",
            surname=data.surname or "",
            phone=data.phone,
        ))
    elif data.role == RoleEnum.employer:
        EmployerRepo.create(db, Employer(user_id=user.id, company_name=""))

    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return TokenResponse(access_token=token)


def login(db: Session, data: LoginRequest) -> TokenResponse:
    user = None
    if data.login_type == "phone" and data.phone:
        user = UserRepo.get_by_phone(db, data.phone)
    elif data.email:
        user = UserRepo.get_by_email(db, data.email)
    elif data.phone:
        user = UserRepo.get_by_phone(db, data.phone)

    if not user or not verify_password(data.password, user.password):
        raise ValueError("Неверный email/телефон или пароль")

    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return TokenResponse(access_token=token)


def change_password(db: Session, user: User, data: ChangePasswordRequest) -> None:
    if not verify_password(data.current_password, user.password):
        raise ValueError("Неверный текущий пароль")
    if len(data.new_password) < 8:
        raise ValueError("Новый пароль должен быть не менее 8 символов")
    user.password = hash_password(data.new_password)
    db.commit()


def update_email(db: Session, user: User, data: UpdateEmailRequest) -> None:
    if not verify_password(data.current_password, user.password):
        raise ValueError("Неверный пароль")
    if data.new_email:
        existing = UserRepo.get_by_email(db, data.new_email)
        if existing and existing.id != user.id:
            raise ValueError("Этот email уже занят")
    user.email = data.new_email or None
    db.commit()

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Vacancy, Application, StatusEnum, VacancyStatusEnum, Employer, Chat, Message, User, Candidate as CandidateModel
from app.repositories.repo import VacancyRepo, ApplicationRepo, EmployerRepo
from app.schemas.vacancy import VacancyCreate, VacancyUpdate, VacancyOut
from app.schemas.application import ApplicationCreate


def _enrich_vacancy(vacancy: Vacancy, db: Session) -> dict:
    employer = EmployerRepo.get_by_id(db, vacancy.employer_id)
    data = {
        "id": vacancy.id,
        "employer_id": vacancy.employer_id,
        "title": vacancy.title,
        "description": vacancy.description,
        "salary": vacancy.salary,
        "city": vacancy.city,
        "education": vacancy.education,
        "experience": vacancy.experience,
        "employment_type": vacancy.employment_type,
        "work_format": vacancy.work_format,
        "requirements": vacancy.requirements,
        "contact_phone": vacancy.contact_phone,
        "contact_email": vacancy.contact_email,
        "status": vacancy.status.value if vacancy.status else None,
        "created_at": vacancy.created_at,
        "company_name": employer.company_name if employer else None,
        "employer_phone": employer.phone if employer else None,
    }
    return data


def create_vacancy(db: Session, employer_user_id: int, data: VacancyCreate) -> Vacancy:
    employer = EmployerRepo.get_by_user_id(db, employer_user_id)
    if employer is None:
        raise ValueError("Employer profile not found")
    vacancy_data = data.model_dump()
    if data.status is None:
        vacancy_data["status"] = VacancyStatusEnum.draft
    vacancy = Vacancy(employer_id=employer.id, **vacancy_data)
    return VacancyRepo.create(db, vacancy)


def update_vacancy(db: Session, vacancy_id: int, employer_user_id: int, data: VacancyUpdate) -> Vacancy:
    vacancy = VacancyRepo.get_by_id(db, vacancy_id)
    if vacancy is None:
        raise ValueError("Vacancy not found")
    employer = EmployerRepo.get_by_user_id(db, employer_user_id)
    if employer is None or vacancy.employer_id != employer.id:
        raise ValueError("Not your vacancy")
    return VacancyRepo.update(db, vacancy, data.model_dump(exclude_unset=True))


def delete_vacancy(db: Session, vacancy_id: int, employer_user_id: int) -> None:
    vacancy = VacancyRepo.get_by_id(db, vacancy_id)
    if vacancy is None:
        raise ValueError("Vacancy not found")
    employer = EmployerRepo.get_by_user_id(db, employer_user_id)
    if employer is None or vacancy.employer_id != employer.id:
        raise ValueError("Not your vacancy")
    VacancyRepo.delete(db, vacancy)


def get_vacancies(db: Session, skip: int = 0, limit: int = 50, city: str | None = None):
    return VacancyRepo.get_all(db, skip, limit, city)


def get_published_vacancies(db: Session, skip: int = 0, limit: int = 50, city: str | None = None, search: str | None = None):
    vacancies = VacancyRepo.get_published(db, skip, limit, city, search)
    return [_enrich_vacancy(v, db) for v in vacancies]


def get_employer_vacancies(db: Session, employer_user_id: int):
    employer = EmployerRepo.get_by_user_id(db, employer_user_id)
    if employer is None:
        raise ValueError("Employer profile not found")
    return [_enrich_vacancy(v, db) for v in VacancyRepo.get_by_employer(db, employer.id)]


def get_vacancy_detail(db: Session, vacancy_id: int) -> dict:
    vacancy = VacancyRepo.get_by_id(db, vacancy_id)
    if vacancy is None:
        raise ValueError("Vacancy not found")
    return _enrich_vacancy(vacancy, db)


def publish_vacancy(db: Session, vacancy_id: int, employer_user_id: int) -> Vacancy:
    vacancy = VacancyRepo.get_by_id(db, vacancy_id)
    if vacancy is None:
        raise ValueError("Vacancy not found")
    employer = EmployerRepo.get_by_user_id(db, employer_user_id)
    if employer is None or vacancy.employer_id != employer.id:
        raise ValueError("Not your vacancy")
    vacancy.status = VacancyStatusEnum.published
    db.commit()
    db.refresh(vacancy)
    return vacancy


def apply_to_vacancy(db: Session, candidate_user_id: int, data: ApplicationCreate) -> dict:
    from app.repositories.repo import CandidateRepo
    from app.models import Chat, Message, Candidate as CandidateModel, Employer as EmployerModel
    candidate = CandidateRepo.get_by_user_id(db, candidate_user_id)
    if candidate is None:
        raise ValueError("Candidate profile not found")
    vacancy = VacancyRepo.get_by_id(db, data.vacancy_id)
    if vacancy is None:
        raise ValueError("Vacancy not found")
    if vacancy.status != VacancyStatusEnum.published:
        raise ValueError("Вакансия не опубликована")

    existing = db.execute(
        select(Application).where(
            Application.vacancy_id == data.vacancy_id,
            Application.candidate_id == candidate.id,
        )
    ).scalar_one_or_none()
    if existing:
        raise ValueError("Вы уже откликались на эту вакансию")

    application = Application(
        vacancy_id=data.vacancy_id,
        candidate_id=candidate.id,
        status=StatusEnum.pending,
    )
    application = ApplicationRepo.create(db, application)

    employer = db.get(EmployerModel, vacancy.employer_id)
    candidate_user = db.get(User, candidate.user_id) if candidate else None
    employer_user = db.get(User, employer.user_id) if employer else None
    candidate_full = ((candidate.name or "") + " " + (candidate.surname or "")).strip()

    chat = Chat(application_id=application.id)
    db.add(chat)
    db.commit()
    db.refresh(chat)

    system_msg = Message(
        chat_id=chat.id,
        sender_id=candidate_user.id if candidate_user else candidate.user_id,
        text="На вашу вакансию «" + (vacancy.title or "") + "» откликнулся кандидат" + ((": " + candidate_full) if candidate_full else ""),
    )
    db.add(system_msg)
    db.commit()
    db.refresh(system_msg)

    return {
        "id": application.id,
        "vacancy_id": application.vacancy_id,
        "candidate_id": application.candidate_id,
        "status": application.status.value,
        "created_at": application.created_at,
        "chat_id": chat.id,
    }


def get_candidate_applications(db: Session, candidate_user_id: int):
    candidate = CandidateRepo.get_by_user_id(db, candidate_user_id)
    if candidate is None:
        raise ValueError("Candidate profile not found")
    return ApplicationRepo.get_by_candidate(db, candidate.id)


def get_vacancy_applications(db: Session, vacancy_id: int):
    return ApplicationRepo.get_by_vacancy(db, vacancy_id)


def get_employer_applications(db: Session, employer_user_id: int) -> list[dict]:
    employer = EmployerRepo.get_by_user_id(db, employer_user_id)
    if employer is None:
        raise ValueError("Employer profile not found")
    vacancies = VacancyRepo.get_by_employer(db, employer.id)
    result = []
    for v in vacancies:
        apps = ApplicationRepo.get_by_vacancy(db, v.id)
        for a in apps:
            candidate = db.get(CandidateModel, a.candidate_id)
            candidate_user = db.get(User, candidate.user_id) if candidate else None
            full_name = ((candidate.name or "") + " " + (candidate.surname or "")).strip() if candidate else "—"
            candidate_email = candidate_user.email if candidate_user else None
            candidate_phone = candidate.phone if candidate else None
            result.append({
                "id": a.id,
                "vacancy_id": a.vacancy_id,
                "candidate_id": a.candidate_id,
                "status": a.status.value,
                "created_at": a.created_at,
                "vacancy_title": v.title,
                "candidate_name": full_name,
                "candidate_email": candidate_email,
                "candidate_phone": candidate_phone,
                "candidate_skills": candidate.skills if candidate else None,
                "candidate_city": candidate.city if candidate else None,
            })
    return result

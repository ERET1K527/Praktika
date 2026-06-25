from sqlalchemy.orm import Session

from app.models import Chat, Message, Application, User, Vacancy, Employer, Candidate, StatusEnum
from app.repositories.repo import ApplicationRepo, VacancyRepo
from app.schemas.chat import MessageCreate, MessageOut, ChatOut


class ChatRepo:
    @staticmethod
    def get_by_application(db: Session, application_id: int) -> Chat | None:
        from sqlalchemy import select
        return db.execute(select(Chat).where(Chat.application_id == application_id)).scalar_one_or_none()

    @staticmethod
    def get_by_id(db: Session, chat_id: int) -> Chat | None:
        return db.get(Chat, chat_id)

    @staticmethod
    def get_by_user(db: Session, user_id: int) -> list[Chat]:
        from sqlalchemy import select, exists
        apps = db.execute(
            select(Application).where(
                (Application.candidate_id.in_(
                    select(Candidate.id).where(Candidate.user_id == user_id)
                )) | (Application.vacancy_id.in_(
                    select(Vacancy.id).where(Vacancy.employer_id.in_(
                        select(Employer.id).where(Employer.user_id == user_id)
                    ))
                ))
            )
        ).scalars().all()
        app_ids = [a.id for a in apps]
        if not app_ids:
            return []
        from sqlalchemy import select as s
        return db.execute(s(Chat).where(Chat.application_id.in_(app_ids))).scalars().all()

    @staticmethod
    def create(db: Session, chat: Chat) -> Chat:
        db.add(chat)
        db.commit()
        db.refresh(chat)
        return chat

    @staticmethod
    def get_messages(db: Session, chat_id: int) -> list[Message]:
        from sqlalchemy import select
        return db.execute(select(Message).where(Message.chat_id == chat_id).order_by(Message.created_at)).scalars().all()


class MessageRepo:
    @staticmethod
    def create(db: Session, message: Message) -> Message:
        db.add(message)
        db.commit()
        db.refresh(message)
        return message


def get_or_create_chat(db: Session, application_id: int, user_id: int) -> Chat:
    application = ApplicationRepo.get_by_id(db, application_id)
    if application is None:
        raise ValueError("Отклик не найден")
    candidate = db.get(Candidate, application.candidate_id)
    vacancy = db.get(Vacancy, application.vacancy_id)
    employer = db.get(Employer, vacancy.employer_id) if vacancy else None
    is_participant = False
    if candidate and candidate.user_id == user_id:
        is_participant = True
    if employer and employer.user_id == user_id:
        is_participant = True
    if not is_participant:
        raise ValueError("Нет доступа к этому чату")

    chat = ChatRepo.get_by_application(db, application_id)
    if chat is None:
        chat = Chat(application_id=application_id)
        chat = ChatRepo.create(db, chat)
    return chat


def send_message(db: Session, chat_id: int, user_id: int, data: MessageCreate) -> MessageOut:
    chat = ChatRepo.get_by_id(db, chat_id)
    if chat is None:
        raise ValueError("Чат не найден")
    application = ApplicationRepo.get_by_id(db, chat.application_id)
    if application is None:
        raise ValueError("Отклик не найден")
    candidate = db.get(Candidate, application.candidate_id)
    vacancy = db.get(Vacancy, application.vacancy_id)
    employer = db.get(Employer, vacancy.employer_id) if vacancy else None
    is_participant = False
    if candidate and candidate.user_id == user_id:
        is_participant = True
    if employer and employer.user_id == user_id:
        is_participant = True
    if not is_participant:
        raise ValueError("Нет доступа к этому чату")
    if application.status == StatusEnum.rejected:
        raise ValueError("Чат заблокирован: работодатель отклонил отклик. Отправка сообщений недоступна")
    message = Message(chat_id=chat_id, sender_id=user_id, text=data.text)
    message = MessageRepo.create(db, message)
    sender = db.get(User, user_id)
    return MessageOut(
        id=message.id,
        chat_id=message.chat_id,
        sender_id=message.sender_id,
        text=message.text,
        created_at=message.created_at,
        sender_email=sender.email if sender else None,
    )


def get_chat_messages(db: Session, chat_id: int, user_id: int) -> list[MessageOut]:
    chat = ChatRepo.get_by_id(db, chat_id)
    if chat is None:
        raise ValueError("Чат не найден")
    application = ApplicationRepo.get_by_id(db, chat.application_id)
    if application is None:
        raise ValueError("Отклик не найден")
    candidate = db.get(Candidate, application.candidate_id)
    vacancy = db.get(Vacancy, application.vacancy_id)
    employer = db.get(Employer, vacancy.employer_id) if vacancy else None
    is_participant = False
    if candidate and candidate.user_id == user_id:
        is_participant = True
    if employer and employer.user_id == user_id:
        is_participant = True
    if not is_participant:
        raise ValueError("Нет доступа к этому чату")
    messages = ChatRepo.get_messages(db, chat_id)
    result = []
    for m in messages:
        sender = db.get(User, m.sender_id)
        result.append(MessageOut(
            id=m.id,
            chat_id=m.chat_id,
            sender_id=m.sender_id,
            text=m.text,
            created_at=m.created_at,
            sender_email=sender.email if sender else None,
        ))
    return result


def get_user_chats(db: Session, user_id: int) -> list[ChatOut]:
    chats = ChatRepo.get_by_user(db, user_id)
    result = []
    for chat in chats:
        application = ApplicationRepo.get_by_id(db, chat.application_id)
        if application is None:
            continue
        vacancy = db.get(Vacancy, application.vacancy_id)
        candidate = db.get(Candidate, application.candidate_id)
        candidate_user = db.get(User, candidate.user_id) if candidate else None
        employer = None
        employer_user = None
        if vacancy:
            employer = db.get(Employer, vacancy.employer_id)
            if employer:
                employer_user = db.get(User, employer.user_id)
        other_email = None
        other_user_id = None
        if candidate and candidate.user_id == user_id:
            other_email = employer_user.email if employer_user else None
            other_user_id = employer.user_id if employer else None
        elif employer and employer.user_id == user_id:
            other_email = candidate_user.email if candidate_user else None
            other_user_id = candidate.user_id if candidate else None
        messages = ChatRepo.get_messages(db, chat.id)
        last_msg = messages[-1].text[:80] if messages else None
        result.append(ChatOut(
            id=chat.id,
            application_id=chat.application_id,
            created_at=chat.created_at,
            vacancy_title=vacancy.title if vacancy else None,
            other_user_email=other_email,
            other_user_id=other_user_id,
            last_message=last_msg,
            application_status=application.status.value if application else None,
        ))
    return result

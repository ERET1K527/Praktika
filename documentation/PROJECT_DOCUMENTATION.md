# JobFlow — Полная документация проекта

> Версия документа: 2.0
> Дата составления: 2026-06-22
> Реквизиты проекта: `SUMMER_PROJECT` (локальная директория)

---

## Оглавление

1. [Общее описание проекта](#1-общее-описание-проекта)
2. [Структура проекта](#2-структура-проекта)
3. [Подробный анализ кода](#3-подробный-анализ-кода)
4. [Подключаемые зависимости](#4-подключаемые-зависимости)
5. [Конфигурации проекта](#5-конфигурации-проекта)
6. [Поток работы приложения](#6-поток-работы-приложения)
7. [Внешние сервисы](#7-внешние-сервисы)
8. [Алгоритм работы проекта](#8-алгоритм-работы-проекта)
9. [Проблемные места проекта](#9-проблемные-места-проекта)
10. [Раздел для нового разработчика](#10-раздел-для-нового-разработчика)

---

## 1. Общее описание проекта

| Параметр | Значение |
|---|---|
| **Название** | JobFlow |
| **Тип** | Веб-приложение (многостраничный сайт + REST API) |
| **Язык бэкенда** | Python 3 (3.12 в Docker) |
| **Фреймворк бэкенда** | FastAPI (ASGI, uvicorn) |
| **Язык фронтенда** | HTML, CSS, JavaScript (ванильный, без сборщика) |
| **База данных** | SQLite (по умолчанию) / PostgreSQL (через SQLAlchemy) |
| **Кэш / брокер** | Redis (объявлен в конфиге, фактически не используется) |
| **Аутентификация** | JWT (HS256) + bcrypt |
| **Деплой** | Docker / docker-compose |

### 1.1 Для чего предназначен проект

JobFlow — это **платформа для поиска работы и подбора персонала** (job-board). Она соединяет две категории пользователей:

- **Соискатели (Candidate)** — публикуют резюме, ищут вакансии, откликаются на них и ведут переписку с работодателями.
- **Работодатели (Employer)** — публикуют вакансии, просматривают резюме соискателей, принимают отклики и общаются с кандидатами в чате.

Также предусмотрен **администратор (Admin)** с панелью управления (`admin.html`): статистика, списки пользователей/кандидатов/работодателей/вакансий/откликов, удаление пользователей и верификация работодателей.

### 1.2 Какие задачи решает

1. Регистрация и авторизация по **email или телефону** с ролевой моделью (candidate / employer / admin).
2. Создание и редактирование профиля кандидата и профиля работодателя.
3. Публикация вакансий (со статусами `draft` / `published`) с указанием города, зарплаты, графика, требований и т.д.
4. Создание и публикация резюме (форма с полями: позиция, зарплата, опыт, навыки, образование, языки и т.д.).
5. Подбор опубликованных вакансий/резюме по городу и поисковой строке.
6. Отклик кандидата на вакансию (`POST /api/vacancies/{id}/apply`) с автоматическим созданием чата.
7. Чат между кандидатом и работодателем, привязанный к отклику (Application).
8. Смена пароля и email в личном кабинете.
9. Сервис «присутствия» (presence) — онлайн-статус пользователей через heartbeat.
10. Административная панель: дашборд, списки сущностей, удаление пользователей, верификация компаний.

### 1.3 Основной принцип работы

Аритектура построена по **трёхуровневой схеме (Layered / Clean-ish)**:

```
[ Браузер (HTML+JS) ] ──HTTP/Fetch──> [ FastAPI Routers (API) ]
                                                │
                                                ▼
                                    [ Services (бизнес-логика) ]
                                                │
                                                ▼
                                    [ Repositories (доступ к данным) ]
                                                │
                                                ▼
                                    [ SQLAlchemy ORM → БД ]
```

- **Фронтенд** — статические HTML-страницы из папки `html/`, которые ходят в REST API через `fetch()`. JWT-токен хранится в `localStorage.jobflow_token`.
- **API-слой** (`app/api/*.py`) — FastAPI-роутеры, валидируют входные данные через Pydantic-схемы, проверяют авторизацию через зависимости (`get_current_user`, `require_role`).
- **Service-слой** (`app/services/*.py`) — бизнес-логика: создание сущностей, проверки прав, отправка сообщений и т.д.
- **Repository-слой** (`app/repositories/repo.py`, а также `ChatRepo`/`MessageRepo` внутри `chat_service.py`) — инкапсулирует запросы к БД.
- **Model-слой** (`app/models/*.py`) — ORM-модели (таблицы БД).
- **Schema-слой** (`app/schemas/*.py`) — Pydantic-модели для запросов/ответов.

### 1.4 Архитектура проекта (высокоуровневая)

```
                ┌──────────────────────────────────────────┐
                │             КЛИЕНТ (браузер)              │
                │  html/index.html, login.html, account.html│
                │  js/nav-auth.js, auth-guard.js,           │
                │  notifications.js, city-loader.js         │
                └───────────────────┬──────────────────────┘
                                    │  HTTP / fetch /api/*
                                    ▼
                ┌──────────────────────────────────────────┐
                │          FastAPI APP (app/main.py)         │
                │  lifespan → create_all + _create_admin     │
                │  CORSMiddleware (allow_origins=*)          │
                │  /static mount + FileResponse на css/js/html│
                └───────────────────┬──────────────────────┘
                                    │  включает router'ы (prefix=/api)
   ┌────────┬──────────┬────────────┼────────────┬──────────┬─────────┐
   ▼        ▼          ▼            ▼            ▼          ▼         ▼
 auth    users      admin       vacancies       chat      resumes   presence
   │        │          │            │            │          │         │
   ▼        ▼          ▼            ▼            ▼          ▼         ▼
              Services (auth, candidate, employer, vacancy,
                        resume, chat, admin, presence)
                                    │
                                    ▼
              Repositories (UserRepo, CandidateRepo, EmployerRepo,
                 VacancyRepo, ApplicationRepo, ResumeRepo, ChatRepo)
                                    │
                                    ▼
              SQLAlchemy ORM (models) → engine → SQLite/Postgres
```

---

## 2. Структура проекта

### 2.1 Дерево файлов

```
SUMMER_PROJECT/
│
├── app/                         # Основной пакет бэкенда (FastAPI-приложение)
│   ├── __init__.py
│   ├── main.py                  # Точка входа FastAPI-приложения
│   │
│   ├── api/                     # HTTP-роутеры (контроллеры)
│   │   ├── __init__.py
│   │   ├── auth.py              # /api/auth/* — регистрация, логин, me, смена пароля/email
│   │   ├── users.py             # /api/users/* — профили candidate/employer
│   │   ├── admin.py             # /api/admin/* — панель администратора
│   │   ├── vacancies.py         # /api/vacancies/* — CRUD вакансий + отклики
│   │   ├── resumes.py           # /api/resumes/* — CRUD резюме + browse
│   │   ├── chat.py              # /api/chat/* — чаты и сообщения
│   │   └── presence.py          # /api/presence/* — heartbeat / online
│   │
│   ├── services/                # Бизнес-логика
│   │   ├── __init__.py
│   │   ├── auth_service.py      # register, login, change_password, update_email
│   │   ├── candidate_service.py
│   │   ├── employer_service.py
│   │   ├── vacancy_service.py   # вакансии, отклики, автоматическое создание чата
│   │   ├── resume_service.py
│   │   ├── chat_service.py      # ChatRepo, MessageRepo, send/get messages
│   │   ├── admin_service.py
│   │   └── presence_service.py  # PresenceRegistry (in-memory)
│   │
│   ├── repositories/            # Слой доступа к данным
│   │   ├── __init__.py
│   │   └── repo.py              # User/Candidate/Employer/Vacancy/Application/Resume repos
│   │
│   ├── models/                  # SQLAlchemy ORM-модели
│   │   ├── __init__.py          # Экспорт всех моделей + __all__
│   │   ├── user.py              # User, RoleEnum
│   │   ├── candidate.py         # Candidate
│   │   ├── employer.py          # Employer
│   │   ├── vacancy.py           # Vacancy, VacancyStatusEnum
│   │   ├── application.py       # Application, StatusEnum
│   │   ├── chat.py              # Chat, Message  (ОБЕ модели в одном файле)
│   │   └── resume.py            # Resume
│   │
│   ├── schemas/                 # Pydantic-схемы (DTO)
│   │   ├── __init__.py
│   │   ├── auth.py              # RegisterRequest, LoginRequest, TokenResponse, UserOut...
│   │   ├── candidate.py
│   │   ├── employer.py
│   │   ├── vacancy.py           # VacancyCreate/Update/Out, VacancyStatusEnum
│   │   ├── resume.py            # ResumeCreate/Update/Out/OutWithCandidate
│   │   ├── application.py       # ApplicationCreate, ApplicationUpdateStatus, ApplicationOut
│   │   └── chat.py              # MessageCreate/Out, ChatOut
│   │
│   ├── core/                    # Ядро: конфиг, безопасность, зависимости
│   │   ├── __init__.py
│   │   ├── config.py            # Settings (pydantic-settings)
│   │   ├── security.py          # hash/verify password (bcrypt), JWT (jose)
│   │   └── deps.py              # get_current_user, require_role, oauth2_scheme
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   └── db.py                # engine, SessionLocal, Base, get_db
│   │
│   ├── static/                  # Папка для статики (пустая, маунтится на /static)
│   └── templates/               # Папка под шаблоны (пустая, не используется)
│
├── migrations/                  # Alembic-миграции
│   ├── env.py                   # target_metadata (импортирует НЕ все модели)
│   └── versions/                # ПУСТАЯ — готовых миграций нет
│
├── html/                        # HTML-страницы фронтенда (12 файлов)
│   ├── index.html               # Главная страница
│   ├── login.html               # Вход
│   ├── register.html            # Регистрация
│   ├── account.html             # Личный кабинет (профиль, отклики, чат)
│   ├── admin.html               # Панель администратора
│   ├── vacancies.html           # Список вакансий
│   ├── resumes-browse.html      # Список резюме (для работодателя)
│   ├── rezume.html              # Карточка резюме
│   ├── sotrudnick.html          # Карточка работодателя
│   ├── city.html                # Выбор города
│   ├── help.html                # Справка
│   └── servise.html             # Услуги / сервисы
│
├── js/                          # Общие JS-скрипты фронтенда
│   ├── auth-guard.js            # Защита страниц: редирект неавторизованных
│   ├── nav-auth.js              # Навигация по роли + поисковая панель
│   ├── city-loader.js           # Загрузка/хранение выбранного города
│   └── notifications.js         # Колокольчик уведомлений (WS + polling)
│
├── css/                         # Стили страниц (12 файлов)
│   ├── index.css, login.css, account.css, vacancies.css, ...
│   ├── register.css, resumes-browse.css, notifications.css
│   └── ... (rezume, sotrudnick, city, help, servise)
│
├── images/                      # Папка под изображения (пустая)
│
├── Python/                      # Вспомогательная папка (placeholder)
│
├── server.py                    # УСТАРЕВШИЙ монолитный бэкенд
│                                # Дублирует app/ — НЕ используется Dockerfile
│
├── requirements.txt             # Python-зависимости (пин версии)
├── .env                         # Переменные окружения (реальные значения)
├── .gitignore
├── Dockerfile                   # Образ приложения (python:3.12-slim)
├── docker-compose.yml           # Оркестрация (web + db + redis)
├── alembic.ini                  # Конфиг Alembic
├── kilo.json                    # Конфиг IDE/инструмента Kilo
├── jobflow.db                   # Файл SQLite-базы данных
└── documentation/
    └── PROJECT_DOCUMENTATION.md # Этот документ
```

### 2.2 Назначение папок

| Папка | Назначение |
|---|---|
| `app/` | Главный Python-пакет. Содержит всё серверное приложение, разбитое на подслои. |
| `app/api/` | HTTP-контроллеры (FastAPI `APIRouter`). Принимают запросы, валидируют, дёргают сервисы. |
| `app/services/` | Бизнес-логика доменов. Здесь сосредоточены правила (например, «только работодатель создаёт вакансию»). |
| `app/repositories/` | Слой доступа к данным (кроме чатов). Изолирует ORM-вызовы от бизнес-логики. |
| `app/models/` | ORM-описания таблиц БД (`DeclarativeBase`). |
| `app/schemas/` | Pydantic-модели для валидации JSON-запросов и формирования ответов. |
| `app/core/` | Сквозная инфраструктура: конфиг, криптография, общие зависимости FastAPI. |
| `app/database/` | Настройка подключения к БД (engine, session factory, Base). |
| `app/static/`, `app/templates/` | Созданы, но фактически пустые. `/static` маунтится в `main.py`. |
| `migrations/` | Alembic: версионные миграции схемы БД. Папка `versions/` пуста. |
| `html/` | Статические HTML-страницы фронтенда (раздаются через `FileResponse`). |
| `js/` | Клиентские скрипты (раздаются через `FileResponse` по `/js/*`). |
| `css/` | Стили страниц (раздаются через `FileResponse` по `/css/*`). |
| `images/` | Под изображения (пустая на текущий момент). |
| `Python/` | Вспомогательная/экспериментальная папка. |
| `documentation/` | Документация проекта (этот файл). |

---

## 3. Подробный анализ кода

> Ниже разобраны ключевые файлы с описанием классов, функций, переменных и их связей (по актуальному состоянию кода).

### 3.1 `app/main.py` — точка входа

| Сущность | Тип | Описание |
|---|---|---|
| `BASE_DIR` | `str` | Корень проекта (`dirname(dirname(__file__))`). Добавляется в `sys.path` для импортов. |
| `lifespan(app)` | async context manager | FastAPI lifespan. При старте вызывает `Base.metadata.create_all(bind=engine)` и `_create_admin()`. |
| `_create_admin()` | функция | Создаёт `admin@jobflow.ru` / `admin123` (роль `admin`), если такого пользователя нет. |
| `app` | `FastAPI` | Главный объект (`title="JobFlow API", version="1.0.0"`, lifespan). |
| `CORSMiddleware` | middleware | **Настроен**: `allow_origins=["*"]`, `allow_credentials=True`, все методы/заголовки. |
| `app.mount("/static", ...)` | вызов | Монтирует `app/static` (папка пустая). |
| HTML/CSS/JS роуты | декораторы | `/` → `html/index.html`; `/{name}.html` → `html/{name}.html`; `/css/{name}.css`; `/js/{name}.js` — через `FileResponse`. |
| `app.include_router(..., prefix="/api")` | вызовы | Подключает: `auth`, `users`, `admin`, `vacancies`, `chat`, `resumes`, `presence`. |

**Важно:** статика `css/` и `js/` отдаётся **не** через `StaticFiles`, а через отдельные GET-роуты `FileResponse`. Папки `/css`, `/js` как mount отсутствуют.

**Зависимости:** `app.database.db`, `app.core.config`, `app.api.*`.
**Кто использует:** `Dockerfile` (`CMD uvicorn app.main:app`), uvicorn при локальном запуске.

### 3.2 `app/core/config.py` — конфигурация

```python
class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./jobflow.db"
    REDIS_URL: str = "redis://localhost:6379/0"
    SECRET_KEY: str = "super-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

settings = Settings()
```

| Сущность | Описание |
|---|---|
| `Settings` | Класс настроек, наследуется от `pydantic_settings.BaseSettings`. Все поля имеют значения по умолчанию, поэтому `.env` опционален. |
| `settings` | Глобальный экземпляр `Settings()`. Импортируется всеми модулями, которым нужны параметры. |

**Зависимости:** `pydantic-settings`, `.env` (если есть).
**Кто использует:** `app.core.security`, `app.database.db`.

### 3.3 `app/core/security.py` — безопасность

| Функция | Параметры | Возвращает | Назначение |
|---|---|---|---|
| `hash_password(password)` | открытый пароль | `str` (bcrypt-хеш) | Хеширование пароля при регистрации/смене. |
| `verify_password(plain, hashed)` | открытый + хеш | `bool` | Проверка пароля при входе/смене. |
| `create_access_token(data, expires_delta=None)` | payload (`sub`, `role`) | `str` (JWT) | Создание подписанного токена, срок = `settings.ACCESS_TOKEN_EXPIRE_MINUTES` (или `expires_delta`). |
| `decode_access_token(token)` | JWT-строка | `dict` payload | Расшифровка токена. |

**Использует напрямую:** `bcrypt` (`hashpw`/`checkpw`/`gensalt`), `jose.jwt`, `settings.SECRET_KEY`, `settings.ALGORITHM`.
> ⚠️ `passlib` из `requirements.txt` фактически не используется — хеширование идёт через `bcrypt` напрямую.

**Кто вызывает:** `auth_service`, `_create_admin` (в `main.py`).

### 3.4 `app/core/deps.py` — зависимости FastAPI

| Сущность | Тип | Назначение |
|---|---|---|
| `oauth2_scheme` | `OAuth2PasswordBearer(tokenUrl="/api/auth/login")` | Извлекает токен из заголовка `Authorization: Bearer ...`. |
| `get_current_user(token, db)` | функция-зависимость | Декодирует JWT, берёт `sub`, находит пользователя через `UserRepo.get_by_id`. Возвращает `User`. 401 при ошибке. |
| `require_role(*roles)` | фабрика зависимостей | Возвращает зависимость, пускает только пользователей с указанными ролями. 403 при недостатке прав. |

**Зависимости:** `app.core.security`, `app.repositories.repo.UserRepo`, `app.models`.
**Кто использует:** все защищённые роутеры `app/api/`.

### 3.5 `app/database/db.py` — подключение к БД

| Сущность | Описание |
|---|---|
| `engine` | `create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})`. |
| `SessionLocal` | `sessionmaker(bind=engine, autocommit=False, autoflush=False)`. |
| `Base` | `class Base(DeclarativeBase): pass` (SQLAlchemy 2.0 стиль). |
| `get_db()` | Генератор-зависимость FastAPI. Открывает сессию, отдаёт её, закрывает в `finally`. |

> `check_same_thread=False` нужен для SQLite; на PostgreSQL параметр игнорируется.
**Кто использует:** все модели, репозитории, сервисы, `main.py` (через `create_all`).

### 3.6 `app/models/` — ORM-модели

#### `user.py`

| Сущность | Тип | Описание |
|---|---|---|
| `RoleEnum` | Enum | `admin`, `employer`, `candidate` (`str, enum.Enum`). |
| `User` | модель | Поля: `id`, `email` (unique, **nullable**), `phone` (unique, **nullable**), `password`, `role`, `created_at`. Связи: `candidate` (one-to-one), `employer` (one-to-one), `cascade="all, delete-orphan"`. |

> Вход возможен **как по email, так и по телефону** — поэтому оба поля опциональны (но хотя бы одно должно быть).

#### `candidate.py`

| `Candidate` | Поля: `id`, `user_id` (FK→users, unique), `name`, `surname`, `phone`, `city`, `skills`, `experience`, `education`, `resume` (Text). Связи: `user`, `applications`, `resumes` (cascade). |

#### `employer.py`

| `Employer` | Поля: `id`, `user_id` (FK, unique), `company_name`, `website`, `description`, `phone`, `verified` (Boolean, default False). Связи: `user`, `vacancies` (cascade). |

#### `vacancy.py`

| `Vacancy`, `VacancyStatusEnum` | Поля: `id`, `employer_id` (FK), `title`, `description`, `salary`, `city`, `education`, `experience`, `employment_type`, `work_format`, `requirements`, `contact_phone`, `contact_email`, `status` (`draft`/`published`, default `draft`), `created_at`. Связи: `employer`, `applications`. |

#### `application.py`

| `Application`, `StatusEnum` | Отклик кандидата на вакансию. Поля: `id`, `vacancy_id` (FK), `candidate_id` (FK), `status` (`pending`/`reviewed`/`accepted`/`rejected`, default `pending`), `created_at`. Связи: `vacancy`, `candidate`, `chat` (one-to-one, cascade). |

#### `chat.py` (содержит ДВЕ модели)

| `Chat` | Поля: `id`, `application_id` (FK→applications, **unique**), `created_at`. Связь: `application`, `messages`. Чат жёстко привязан к отклику, а не к паре кандидат/работодатель. |
| `Message` | Поля: `id`, `chat_id` (FK), `sender_id` (FK→users), `text`, `created_at`. Связи: `chat`, `sender`. |

> Отдельного файла `message.py` **нет** — обе модели в `chat.py`.

#### `resume.py`

| `Resume` | Поля: `id`, `candidate_id` (FK), `title` (default «Моё резюме»), `position`, `salary`, `employment`, `city`, `education`, `skills`, `experience`, `about`, `languages`, `driving`, `status` (default `draft`), `created_at`, `updated_at`. Связь: `candidate`. |

> Это **форма-резюме** (набор текстовых полей), а не загружаемый файл. Полей `file_path`/`description` нет.

### 3.7 `app/repositories/repo.py` — репозитории

Все репозитории реализованы как классы со статическими методами, принимают `db: Session` первым аргументом. Поддерживают пагинацию (`skip`/`limit`).

| Класс | Ключевые методы | Сущность |
|---|---|---|
| `UserRepo` | `get_by_email`, `get_by_phone`, `get_by_id`, `create`, `get_all(skip, limit)`, `delete` | `User` |
| `CandidateRepo` | `get_by_user_id`, `get_by_id`, `create`, `update`, `get_all(skip, limit)` | `Candidate` |
| `EmployerRepo` | `get_by_user_id`, `get_by_id`, `create`, `update`, `get_all(skip, limit)` | `Employer` |
| `VacancyRepo` | `get_by_id`, `create`, `update`, `delete`, `get_all(skip, limit, city)`, `get_published(skip, limit, city, search)`, `get_by_employer` | `Vacancy` |
| `ApplicationRepo` | `create`, `get_by_id`, `update_status`, `get_by_candidate`, `get_by_vacancy`, `get_all(skip, limit)` | `Application` |
| `ResumeRepo` | `create`, `get_by_id`, `get_by_candidate`, `update`, `get_published(skip, limit, city, search, position)`, `delete` | `Resume` |

> `ChatRepo` и `MessageRepo` определены **внутри** `app/services/chat_service.py` (а не в `repo.py`).

**Кто использует:** сервисы из `app/services/`.

### 3.8 `app/services/` — бизнес-логика

| Файл | Функции/классы | Назначение |
|---|---|---|
| `auth_service.py` | `register`, `login`, `change_password`, `update_email` | Регистрация по email/телефону с авто-созданием профиля Candidate/Employer; проверка уникальности; смена пароля (≥8 символов) и email. |
| `candidate_service.py` | `get_my_profile`, `create_profile`, `update_profile`, `get_all_candidates` | CRUD профиля кандидата (профиль создаётся при регистрации, здесь — обновление). |
| `employer_service.py` | `get_my_profile`, `create_profile`, `update_profile`, `get_all_employers` | Аналогично для employer. |
| `vacancy_service.py` | `create_vacancy`, `update_vacancy`, `delete_vacancy`, `publish_vacancy`, `get_published_vacancies`, `get_employer_vacancies`, `get_vacancy_detail`, `apply_to_vacancy`, `get_candidate_applications`, `get_vacancy_applications`, `get_employer_applications`, `_enrich_vacancy` | Вакансии + отклики. **`apply_to_vacancy`** создаёт `Application(pending)`, тут же создаёт `Chat` и системное сообщение об отклике. Возвращает словарь с `chat_id`. |
| `resume_service.py` | `list_resumes`, `browse_published_resumes`, `get_resume`, `create_resume`, `update_resume`, `delete_resume`, `publish_resume` | Резюме: при создании поля дефолтятся из профиля кандидата (город/образование/навыки/опыт). |
| `chat_service.py` | `ChatRepo`, `MessageRepo`, `get_or_create_chat`, `send_message`, `get_chat_messages`, `get_user_chats` | Диалоги. `send_message` **блокируется**, если `application.status == rejected`. Проверяет участие пользователя в чате. |
| `admin_service.py` | `get_dashboard`, `list_users`, `list_candidates`, `list_employers`, `list_vacancies`, `list_applications`, `delete_user`, `verify_employer` | Админ-функции. |
| `presence_service.py` | `PresenceRegistry`, синглтон `presence` | In-memory реестр онлайн-пользователей по `user_id` с TTL 60 c. Методы: `heartbeat`, `online_user_ids(exclude)`, `is_online`. Не персистится. |

### 3.9 `app/api/` — роутеры

> Все роутеры подключаются с общим префиксом `/api`. Каждый `APIRouter` имеет свой `prefix` и `tags`.

| Файл | Префикс | Эндпоинты | Защита |
|---|---|---|---|
| `auth.py` | `/api/auth` | `POST /register`, `POST /login`, `GET /me`, `POST /change-password`, `POST /update-email` | первые два — открытые; остальные — JWT |
| `users.py` | `/api/users` | `GET/POST/PUT /candidate/profile`, `GET/POST/PUT /employer/profile` | `require_role(candidate\|employer)` |
| `admin.py` | `/api/admin` | `GET /dashboard`, `GET /users`, `GET /candidates`, `GET /employers`, `GET /vacancies`, `GET /applications`, `DELETE /users/{id}`, `POST /employers/{id}/verify` | `require_role("admin")` |
| `vacancies.py` | `/api/vacancies` | `GET /`, `GET /my`, `GET /my/applications`, `GET /employer/applications`, `POST /`, `GET /{id}`, `POST /{id}/publish`, `PUT /{id}`, `DELETE /{id}`, `POST /{id}/apply`, `GET /{id}/applications` | смешанная (см. таблицу ниже) |
| `resumes.py` | `/api/resumes` | `GET /`, `POST /`, `GET /browse`, `GET /{id}`, `GET /candidate/{id}`, `PUT /{id}`, `DELETE /{id}`, `POST /{id}/publish` | смешанная |
| `chat.py` | `/api/chat` | `GET /chats`, `POST /application/{application_id}`, `GET /{chat_id}/messages`, `POST /{chat_id}/messages` | JWT |
| `presence.py` | `/api/presence` | `POST /heartbeat`, `GET /online` | JWT |

#### Защита эндпоинтов `/api/vacancies`

| Эндпоинт | Доступ |
|---|---|
| `GET /`, `GET /{id}` | открытые |
| `GET /{id}/applications` | `get_current_user` (любой аутентифицированный) |
| `GET /my`, `GET /employer/applications`, `POST /`, `POST /{id}/publish`, `PUT /{id}`, `DELETE /{id}` | `require_role("employer")` |
| `GET /my/applications`, `POST /{id}/apply` | `require_role("candidate")` |

#### Защита эндпоинтов `/api/resumes`

| Эндпоинт | Доступ |
|---|---|
| `GET /`, `POST /`, `PUT /{id}`, `DELETE /{id}`, `POST /{id}/publish` | `require_role("candidate")` |
| `GET /browse`, `GET /candidate/{id}` | `require_role("employer", "admin")` |
| `GET /{id}` | `get_current_user` + разная логика по роли |

### 3.10 `app/schemas/` — Pydantic-модели

| Файл | Ключевые классы |
|---|---|
| `auth.py` | `RoleEnum`, `RegisterRequest` (email/phone/password/role/first_name/surname), `LoginRequest` (email/phone/password/login_type), `TokenResponse`, `UserOut`, `ChangePasswordRequest`, `UpdateEmailRequest` |
| `candidate.py` | `CandidateCreate`, `CandidateUpdate`, `CandidateOut`, `CandidateOutAdmin` |
| `employer.py` | `EmployerCreate`, `EmployerUpdate`, `EmployerOut` (включает `verified`) |
| `vacancy.py` | `VacancyStatusEnum`, `VacancyCreate`, `VacancyUpdate`, `VacancyOut` (включает `company_name`, `employer_phone`) |
| `resume.py` | `ResumeCreate`, `ResumeUpdate`, `ResumeOut`, `ResumeOutWithCandidate` |
| `application.py` | `StatusEnum`, `ApplicationCreate`, `ApplicationUpdateStatus`, `ApplicationOut` |
| `chat.py` | `MessageCreate` (`text`), `MessageOut` (включает `sender_email`), `ChatOut` (включает `vacancy_title`, `other_user_email`, `other_user_id`, `last_message`, `application_status`) |

> Файла `schemas/user.py` нет — DTO пользователя живут в `schemas/auth.py`.

### 3.11 Фронтенд-файлы

#### `js/auth-guard.js`

| Назначение |
|---|
| Защита страниц. На каждом запросе проверяет `jobflow_token`, декодирует `exp` payload без проверки подписи. Если токена нет/истёк — чистит его и редиректит на `login.html` (кроме самих auth-страниц). Если авторизован и зашёл на `login.html`/`register.html` — редирект на `index.html`. |

#### `js/nav-auth.js`

| Функция | Назначение |
|---|---|
| inline-логика | Если есть токен: убирает ссылки «Войти»/«rezume», добавляет «Аккаунт». Запрашивает `/api/auth/me`; при 401 чистит токен и редиректит. По роли фильтрует пункты меню (`.nav-links`) и колонки футера. |
| поисковая панель | Динамически строит плавающую панель поиска (должность + город), редиректит на `vacancies.html?search=...&city=...`. |
| `window.JobFlowNav.openSearchPanel()` | Публичный API для открытия панели. |

#### `js/city-loader.js`

| Назначение |
|---|
| Применяет сохранённый город (`localStorage.jobflow_city`): подставляет в ссылку `.nav-right a[href="city.html"]` и в `#cityInput`. Реагирует на `storage`-событие для синхронизации между вкладками. |

#### `js/notifications.js`

| Назначение |
|---|
| Виджет «колокольчик» уведомлений в `.nav-right`. Загружает список/счётчик непрочитанных, показывает дропдаун и toast. **Использует WebSocket** к `/ws/notifications` (через одноразовый тикет `/api/notifications/ws-ticket`) + **fallback-polling** на `/api/notifications/unread-count` каждые 30 c. |

> ⚠️ **Несогласованность:** скрипт обращается к эндпоинтам `/api/notifications/*` и WebSocket `/ws/notifications`, которых **нет в бэкенде** (`app/api/` и `app/main.py`). Соответствующие запросы будут падать с 404, виджет не получит данных. См. раздел 9.

#### HTML-страницы (`html/`)

| Файл | Назначение | Ключевые API-вызовы |
|---|---|---|
| `index.html` | Главная: поиск, переходы по городу | `GET /api/vacancies` |
| `login.html` | Форма входа (email/телефон) | `POST /api/auth/login` |
| `register.html` | Регистрация (candidate/employer) | `POST /api/auth/register` |
| `account.html` | Личный кабинет: профиль, отклики, чат | `GET /api/users/.../profile`, `POST /api/chat/...` |
| `admin.html` | Панель администратора | `GET /api/admin/*`, `DELETE /api/admin/users/{id}` |
| `vacancies.html` | Список вакансий по городу/поиску | `GET /api/vacancies` |
| `resumes-browse.html` | Список резюме (для работодателя) | `GET /api/resumes/browse` |
| `rezume.html` | Карточка одного резюме | `GET /api/resumes/{id}` |
| `sotrudnick.html` | Карточка работодателя | профиль employer |
| `city.html` | Выбор города | локально, `city-loader.js` |
| `help.html` | Статическая справка | нет |
| `servise.html` | Статическая страница услуг | нет |

#### CSS-файлы (`css/`)

12 файлов, по одному на страницу: `index.css`, `login.css`, `register.css`, `account.css`, `vacancies.css`, `resumes-browse.css`, `rezume.css`, `sotrudnick.css`, `city.css`, `help.css`, `servise.css`, `notifications.css`.

> Общего `style.css` и `form.css` (упоминавшихся в прошлой версии документа) **нет**.

### 3.12 `server.py` — устаревший монолит

Монолитный бэкенд в корне проекта, дублирующий логику `app/`. **Не используется** `Dockerfile` (там `app.main:app`). Рекомендуется удалить после подтверждения, что `app/` полностью покрывает функциональность.

### 3.13 `Python/main.py`

Placeholder/экспериментальная папка. Не влияет на работу приложения.

---

## 4. Подключаемые зависимости

### 4.1 `requirements.txt` (пин версии)

| Библиотека | Версия (pin) | Назначение | Где используется |
|---|---|---|---|
| `fastapi` | 0.111.0 | Веб-фреймворк, роутинг, валидация | `app/main.py`, `app/api/*`, `app/core/deps.py` |
| `uvicorn[standard]` | 0.30.1 | ASGI-сервер запуска приложения | `Dockerfile`, запуск |
| `sqlalchemy` | 2.0.31 | ORM, работа с БД | `app/models/*`, `app/database/db.py`, `app/repositories/*` |
| `psycopg2-binary` | 2.9.9 | Драйвер PostgreSQL | `docker-compose` (для прод-БД) |
| `alembic` | 1.13.1 | Миграции схемы БД | `migrations/` |
| `pydantic` | 2.7.4 | Валидация данных | `app/schemas/*` |
| `pydantic-settings` | 2.3.4 | Чтение `.env` в Settings | `app/core/config.py` |
| `python-jose[cryptography]` | 3.3.0 | Создание/проверка JWT | `app/core/security.py` |
| `passlib[bcrypt]` | 1.7.4 | Хеширование паролей | **фактически НЕ используется** — см. примечание |
| `python-multipart` | 0.0.9 | Парсинг multipart/form-data | потенциально для загрузки файлов |
| `redis` | 5.0.7 | Клиент Redis (кэш/сессии) | объявлен, но в коде не используется |
| `python-dotenv` | 1.0.1 | Загрузка `.env` | `app/core/config.py` |
| `aiofiles` | 23.2.1 | Асинхронная работа с файлами | потенциально раздача статики |

> ⚠️ **Примечание:** `app/core/security.py` импортирует и использует `bcrypt` **напрямую** (`import bcrypt`), а не через `passlib`. При этом прямого пина `bcrypt` в `requirements.txt` нет — он приходит транзитивно через `passlib[bcrypt]`. Это допустимо, но хрупко; рекомендуется либо убрать `passlib`, либо добавить явный `bcrypt` в `requirements.txt`.

### 4.2 Другие менеджеры зависимостей

| Файл | Статус |
|---|---|
| `package.json` | **отсутствует** — фронтенд без сборки (ванильный JS) |
| `pyproject.toml` | отсутствует |
| `Cargo.toml` | отсутствует |
| `pom.xml` | отсутствует |
| `composer.json` | отсутствует |
| `go.mod` | отсутствует |

Вывод: проект зависит только от Python-экосистемы (`requirements.txt`).

---

## 5. Конфигурации проекта

### 5.1 `.env`

```dotenv
DATABASE_URL=sqlite:///./jobflow.db
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=super-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

| Переменная | Значение по умолчанию | Назначение |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./jobflow.db` | Строка подключения к БД. Для Postgres: `postgresql+psycopg2://user:pass@host:5432/db`. |
| `REDIS_URL` | `redis://localhost:6379/0` | Адрес Redis. В коде **не используется**. |
| `SECRET_KEY` | `super-secret-key-change-in-production` | Секрет для подписи JWT. **Должен быть заменён в проде.** |
| `ALGORITHM` | `HS256` | Алгоритм подписи JWT. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Время жизни access-токена (минут). |

### 5.2 `Dockerfile`

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- Базовый образ: **`python:3.12-slim`**.
- Устанавливает зависимости из `requirements.txt`.
- Запускает **`app.main:app`** (не `server.py`).
- Слушает порт 8000.

### 5.3 `docker-compose.yml`

| Сервис | Образ/сборка | Назначение |
|---|---|---|
| `web` | сборка из `Dockerfile` | Само приложение FastAPI. Порт 8000. Зависит от `db` и `redis`. Маунтит `./app/static`. |
| `db` | `postgres:16` | База данных PostgreSQL (прод-режим). Учётка `jobflow/jobflow123`, БД `jobflow`. |
| `redis` | `redis:7-alpine` | Кэш/брокер. |

Передаёт переменные окружения (`DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`) в контейнер `web`.

### 5.4 `alembic.ini` и `migrations/env.py`

- `alembic.ini` — общие настройки Alembic; `sqlalchemy.url = postgresql://jobflow:jobflow123@localhost:5432/jobflow`.
- `migrations/env.py` — точка входа Alembic. `target_metadata = Base.metadata`.

> ⚠️ **Проблема 1:** `env.py` импортирует только `User, Candidate, Employer, Vacancy, Application`. Модели `Chat, Message, Resume` **не включены** явно в импорт. (Они попадут в `Base.metadata` лишь при условии, что загружены через цепочку импортов — фактически это не гарантировано.)
> ⚠️ **Проблема 2:** папка `migrations/versions/` **пуста** — готовых миграций не сгенерировано. Таблицы создаются через `Base.metadata.create_all` в `lifespan`.

### 5.5 `.gitignore`

Игнорирует: `.env`, `__pycache__/`, `*.pyc`, `*.pyo`, `venv/`, `.pgdata`, `migrations/versions/*.pyc`.

> ⚠️ **Не игнорирует:** `.venv/` (только `venv/`), `jobflow.db`, `.idea/`. Если используется `.venv` или SQLite-файл, они могут попасть в репозиторий.

### 5.6 `kilo.json`

Конфигурация AI-инструмента Kilo. Не влияет на runtime.

### 5.7 Конфиги фронтенда

- **Сборщики (vite/webpack/babel):** отсутствуют.
- **Линтеры (eslint/prettier/tsconfig):** отсутствуют.
- Фронтенд — «голые» HTML/CSS/JS, подключаемые напрямую через `<link>` и `<script>`.

---

## 6. Поток работы приложения

### 6.1 Запуск приложения

```
uvicorn app.main:app
        │
        ▼
1. Читается app/core/config.py → .env загружается в Settings (поля имеют дефолты)
2. app/database/db.py создаёт engine (sqlite/postgres)
3. FastAPI lifespan (app/main.py):
     a) Base.metadata.create_all(bind=engine) — создаются таблицы
     b) _create_admin() — создаётся admin@jobflow.ru
4. Подключается CORSMiddleware (allow_origins=["*"])
5. Маунтится /static; регистрируются FileResponse-роуты (/, /{name}.html, /css/*, /js/*)
6. Регистрируются роутеры с prefix="/api" (auth, users, admin, vacancies, chat, resumes, presence)
7. uvicorn начинает слушать порт 8000
```

### 6.2 Жизненный цикл HTTP-запроса

```
Клиент (fetch) ──> FastAPI middleware (CORS)
        │
        ▼
   Роутер (app/api/*.py)
        │  - валидация Pydantic-схемой (422 при ошибке)
        │  - зависимости: get_db, get_current_user, require_role
        ▼
   Сервис (app/services/*.py)  ── бизнес-логика
        │
        ▼
   Репозиторий (repo.py / chat_service.ChatRepo) ── ORM-запрос
        │
        ▼
   SQLAlchemy → БД (SQLite/Postgres)
        │
        ▼
   Результат → Pydantic-схема ответа → JSON → клиент
```

### 6.3 Авторизация (JWT)

```
1. POST /api/auth/register {email|phone, password, role, ...}
        → auth_service.register
        → проверка уникальности email/телефона
        → UserRepo.create (пароль хешируется bcrypt)
        → авто-создание Candidate или Employer (по роли)
        → ответ: {access_token, token_type: "bearer"}

2. POST /api/auth/login {email|phone, password, login_type?}
        → auth_service.login
        → поиск по email ИЛИ телефону
        → verify_password (bcrypt)
        → create_access_token (jose, HS256)
        → ответ: {access_token, token_type: "bearer"}

3. Последующие запросы:
        Заголовок: Authorization: Bearer <token>
        → deps.get_current_user декодирует JWT
        → UserRepo.get_by_id(sub)
        → пользователь доступен в роуте

4. Дополнительно: POST /api/auth/change-password, POST /api/auth/update-email
```

Хранение на клиенте: `localStorage.jobflow_token`.
Срок жизни: `ACCESS_TOKEN_EXPIRE_MINUTES` (60 мин по умолчанию).

### 6.4 Работа с API (примеры)

| Действие | Метод | URL | Тело / Защита |
|---|---|---|---|
| Регистрация | POST | `/api/auth/register` | `{email\|phone, password, role, first_name, surname}` |
| Вход | POST | `/api/auth/login` | `{email\|phone, password, login_type?}` |
| Текущий пользователь | GET | `/api/auth/me` | JWT |
| Сменить пароль | POST | `/api/auth/change-password` | `{current_password, new_password}` |
| Профиль кандидата | GET/POST/PUT | `/api/users/candidate/profile` | JWT(candidate) |
| Профиль работодателя | GET/POST/PUT | `/api/users/employer/profile` | JWT(employer) |
| Опубликованные вакансии | GET | `/api/vacancies?city=&search=` | — |
| Мои вакансии | GET | `/api/vacancies/my` | JWT(employer) |
| Создать вакансию | POST | `/api/vacancies` | `{title, salary, city, ...}` |
| Опубликовать | POST | `/api/vacancies/{id}/publish` | JWT(employer) |
| Откликнуться | POST | `/api/vacancies/{id}/apply` | JWT(candidate) → вернёт `chat_id` |
| Список резюме (свой) | GET | `/api/resumes` | JWT(candidate) |
| Каталог резюме | GET | `/api/resumes/browse?city=&search=&position=` | JWT(employer, admin) |
| Список чатов | GET | `/api/chat/chats` | JWT |
| Открыть/создать чат | POST | `/api/chat/application/{application_id}` | JWT |
| Сообщения | GET/POST | `/api/chat/{chat_id}/messages` | POST: `{text}` |
| Дашборд | GET | `/api/admin/dashboard` | JWT(admin) |
| Удалить пользователя | DELETE | `/api/admin/users/{id}` | JWT(admin) |
| Верифицировать компанию | POST | `/api/admin/employers/{id}/verify` | JWT(admin) |
| Heartbeat (online) | POST | `/api/presence/heartbeat` | JWT |
| Кто онлайн | GET | `/api/presence/online` | JWT |

### 6.5 Работа с базой данных

- SQLAlchemy 2.0 (синхронный режим), `DeclarativeBase`.
- `get_db()` открывает сессию на время запроса и закрывает в `finally`.
- По умолчанию — SQLite-файл `jobflow.db` в корне проекта.
- В Docker — PostgreSQL.
- Таблицы создаются через `Base.metadata.create_all` в `lifespan`. Alembic-миграций пока нет (`versions/` пуст).

### 6.6 Обработка ошибок

- FastAPI автоматически возвращает `422 Unprocessable Entity` при ошибке валидации Pydantic.
- Сервисы бросают `ValueError`; роутеры перехватывают его и возвращают **400/401/404** с текстом ошибки.
- `get_current_user` → `401` при невалидном/просроченном токене.
- `require_role` → `403` при недостатке прав.
- На фронтенде ошибки обрабатываются в `fetch().then()` / `catch()`; `auth-guard.js` и `nav-auth.js` при 401 чистят токен и редиректят на `login.html`.

---

## 7. Внешние сервисы

| Сервис | Тип | Назначение | Настройка |
|---|---|---|---|
| **SQLite** | БД (по умолчанию) | Локальное хранилище для разработки | `DATABASE_URL=sqlite:///./jobflow.db` |
| **PostgreSQL** | БД (прод) | Реляционная БД для production | `docker-compose.yml`, сервис `db` |
| **Redis** | Кэш/брокер | Объявлен в конфиге/компоузе, в коде **не используется** | `REDIS_URL`, сервис `redis` |

### 7.1 API сторонних сервисов

- Внешние HTTP-API (платёжки, SMS, карты) **не подключены**.
- Загрузка городов идёт из локального источника (`city-loader.js` оперирует `localStorage`).
- Нет интеграций с облачными хранилищами (S3 и т.п.) — файлы не загружаются (резюме — это форма, а не файл).

### 7.2 SDK

Внешние SDK отсутствуют. Все зависимости — стандартные Python-библиотеки (см. раздел 4).

---

## 8. Алгоритм работы проекта

### 8.1 Полный жизненный цикл (последовательно)

```
┌─────────────────────────────────────────────────────────────┐
│ 1. ЗАПУСК                                                    │
│    uvicorn app.main:app                                      │
│    → чтение .env (опционально, есть дефолты)                 │
│    → инициализация SQLAlchemy engine                         │
│    → lifespan: create_all + _create_admin                    │
│    → CORS allow_origins=["*"]                                │
│    → uvicorn слушит :8000                                    │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. РЕГИСТРАЦИЯ ПОЛЬЗОВАТЕЛЯ                                  │
│    register.html → POST /api/auth/register                   │
│    → auth_service.register                                   │
│    → UserRepo.create (bcrypt hash)                           │
│    → создаётся профиль Candidate/Employer (пустой, по роли)  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. ВХОД                                                      │
│    login.html → POST /api/auth/login (email ИЛИ телефон)     │
│    → verify_password                                         │
│    → create_access_token → JWT в localStorage.jobflow_token  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. РАБОТА В ЛИЧНОМ КАБИНЕТЕ                                  │
│    account.html (навигация зависит от роли)                  │
│    → GET/PUT /api/users/candidate/profile                    │
│    → GET/PUT /api/users/employer/profile                     │
│    → auth-guard.js проверяет токен на каждой странице        │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. ВЗАИМОДЕЙСТВИЕ РЫНКА                                      │
│    Работодатель: POST /api/vacancies (draft)                 │
│                  POST /api/vacancies/{id}/publish            │
│    Кандидат:    POST /api/resumes + /{id}/publish            │
│    Поиск:       GET /api/vacancies?city=&search=             │
│                 GET /api/resumes/browse?city=&position=      │
│    Отклик:      POST /api/vacancies/{id}/apply               │
│                 → создаётся Application(pending) + Chat      │
│                 + системное сообщение                        │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. ЧАТ                                                       │
│    GET  /api/chat/chats (список по пользователю)             │
│    POST /api/chat/application/{id} (get_or_create_chat)      │
│    POST /api/chat/{chat_id}/messages (send_message)          │
│    GET  /api/chat/{chat_id}/messages                         │
│    ⛔ отправка блокируется при application.status == rejected │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 7. АДМИНИСТРИРОВАНИЕ                                         │
│    admin.html                                                │
│    GET  /api/admin/dashboard, /users, /candidates,           │
│         /employers, /vacancies, /applications                │
│    DELETE /api/admin/users/{id}                              │
│    POST /api/admin/employers/{id}/verify                     │
└─────────────────────────────────────────────────────────────┘
```

### 8.2 Сценарий «Кандидат откликается на вакансию»

```
Кандидат ──GET /api/vacancies──> список опубликованных вакансий
   │
   ├── выбирает вакансию
   ▼
POST /api/vacancies/{id}/apply
   │  (vacancy_service.apply_to_vacancy)
   ▼
проверка: профиль кандидата существует, вакансия published,
          ещё не откликался
   │
   ▼
ApplicationRepo.create → status=pending
   │
   ▼
создаётся Chat(application_id=application.id) + системное Message
   │
   ▼
Работодатель ──GET /api/vacancies/employer/applications──> видит отклик
   │  (или GET /api/vacancies/{id}/applications)
   ▼
Общение: GET/POST /api/chat/{chat_id}/messages
```

### 8.3 Сценарий «Чат»

```
account.html
   │
   ├── GET /api/chat/chats → список чатов с last_message и other_user
   ▼
Открытие диалога:
   POST /api/chat/application/{id} (get_or_create_chat)
   GET  /api/chat/{chat_id}/messages → chat_service.get_chat_messages
                                       → ChatRepo.get_messages
   ▼
Отправка:
   POST /api/chat/{chat_id}/messages {text}
   → проверка участия + статуса отклика (не rejected)
   → MessageRepo.create
   ▼
JSON {id, chat_id, sender_id, text, created_at, sender_email}
```

### 8.4 Сценарий «Присутствие (presence)»

```
Клиент (участок логики, где нужен онлайн-статус)
   │
   ├── POST /api/presence/heartbeat → presence.heartbeat(user_id)
   │      (обновляет timestamp в in-memory реестре)
   ▼
GET /api/presence/online → presence.online_user_ids(exclude=me)
   │  (выбрасывает тех, у кого последний heartbeat старше 60 c)
   ▼
[ список id онлайн-пользователей ]
```

> Реестр `presence` хранится **в оперативной памяти процесса** и не персистится; при перезапуске сбрасывается.

---

## 9. Проблемные места проекта

### 9.1 Дублирование кода

| Проблема | Где | Рекомендация |
|---|---|---|
| `server.py` дублирует `app/` (устаревший монолит) | `server.py` | Удалить после аудита, что `app/` покрывает весь функционал. |
| `ChatRepo`/`MessageRepo` живут в сервисе, а не в репозитории | `app/services/chat_service.py` | Перенести в `app/repositories/` для единообразия. |
| Отсутствует переиспользуемый базовый класс репозитория | `app/repositories/repo.py` | Ввести `BaseRepository[Model]` с типовыми CRUD. |
| Логика навигации/поисковой панели повторяется в HTML | `html/*.html`, `js/nav-auth.js` | Вынести в общий шаблон/компонент. |

### 9.2 Потенциальные ошибки и несогласованности

| Проблема | Где | Риск |
|---|---|---|
| **`notifications.js` обращается к `/api/notifications/*` и `/ws/notifications`, которых нет в бэкенде** | `js/notifications.js` vs `app/api/`, `app/main.py` | Виджет уведомлений неработоспособен: все запросы падают с 404, WebSocket не поднимается. Либо реализовать бэкенд уведомлений, либо убрать скрипт. |
| Модели `Chat, Message, Resume` не импортированы явно в Alembic `target_metadata` | `migrations/env.py` | При автогенерации Alembic может «не увидеть» эти таблицы. |
| Папка `migrations/versions/` пуста | `migrations/versions/` | Готовых миграций нет; схема создаётся только `create_all`. |
| `passlib` в `requirements.txt`, но `security.py` использует `bcrypt` напрямую | `requirements.txt`, `app/core/security.py` | Лишняя зависимость; зависимость от `bcrypt` неявная (транзитивная). |
| `CORSMiddleware` с `allow_origins=["*"]` + `allow_credentials=True` | `app/main.py` | Небезопасная комбинация; браузеры блокируют credential-запросы при `*`. |
| Несинхронизированные версии зависимостей возможны между `requirements.txt` и локальным окружением | `requirements.txt` | Поведение прод-сборки может отличаться от локального. |
| `SECRET_KEY` захардкожен в `.env` и `docker-compose.yml` | `.env`, `docker-compose.yml` | Компрометация JWT при утечке. |
| Автосоздание admin с фиксированным паролем `admin123` | `app/main.py` (`_create_admin`) | В проде — критическая уязвимость. |

### 9.3 Узкие места производительности

| Проблема | Где | Рекомендация |
|---|---|---|
| `admin_service.get_dashboard` грузит по 10 000 записей и считает `len()` | `app/services/admin_service.py` | Использовать `SELECT COUNT(*)`. |
| `get_user_chats`/`get_employer_applications` делают N+1 запросов (`db.get` в цикле) | `app/services/chat_service.py`, `vacancy_service.py` | Переписать на join/selectinload. |
| `_enrich_vacancy` дёргает `EmployerRepo.get_by_id` на каждую вакансию | `app/services/vacancy_service.py` | Тянуть работодателей пакетом. |
| Polling чата на фронтенде | `html/account.html` | Перейти на WebSocket для сообщений (как сделано в `notifications.js`). |
| Пагинация есть (`skip`/`limit`), но без сортировки по релевантности | репозитории | Добавить сортировку/полнотекстовый поиск. |
| Синхронный SQLAlchemy в ASGI-приложении | `app/database/db.py` | Либо async SQLAlchemy, либо осознание, что операции блокируют event-loop. |
| `create_all` в lifespan при каждом старте | `app/main.py` | Использовать Alembic для миграций. |
| In-memory `presence` не шарится между воркерами | `app/services/pence_service.py` | При >1 uvicorn-воркере онлайн-статусы разъедутся; нужен Redis-бэкенд. |

### 9.4 Нарушения архитектуры

| Проблема | Рекомендация |
|---|---|
| Бизнес-логика частично «протекает» в роутеры (например, сборка `ChatOut` прямо в `app/api/chat.py`) | Полностью вынести формирование ответов в сервисы. |
| Репозитории — статические методы без интерфейсов | Ввести протоколы/абстрактные базовые классы для тестируемости. |
| HTML-страницы лежат в `html/`, но `app/templates/` пуст | Либо перенести шаблоны туда и использовать шаблонизатор (Jinja2), либо удалить папку. |
| Несоответствие фронт/бэкенд по уведомлениям | Привести к единому контракту (см. 9.2). |

### 9.5 Технический долг

- Унаследованный `server.py`.
- Пустые папки `app/static/`, `app/templates/`, `images/` (назначение неясно / не используются).
- Отсутствие тестов (нет папки `tests/`, pytest не подключён).
- Нет CI/CD (нет `.github/workflows/`, GitLab CI).
- Нет логирования (не используется модуль `logging`).
- Нет версионирования API (`/api/v1/...`).
- `.env` хранится в репозитории (есть в `.gitignore`, но сам файл присутствует).

### 9.6 Риски безопасности

| Риск | Уровень | Рекомендация |
|---|---|---|
| Захардкоженный `SECRET_KEY` | Высокий | Генерировать случайный ключ, хранить вне репозитория. |
| Дефолтный админ `admin123` | Высокий | Отключить в проде или требовать смену пароля. |
| CORS `allow_origins=["*"]` с credentials | Высокий | Настроить whitelist конкретных доменов. |
| Файлы (если появятся) без проверки типа/размера | Средний | Валидировать MIME и лимит размера. |
| JWT без refresh-токена | Средний | Ввести refresh-токены, сократить lifetime access. |
| Проверка `exp` на клиенте (`auth-guard.js`) без проверки подписи | Низкий | Только UX-фича; реальная проверка — на сервере. |
| SQL-инъекции | Низкий | SQLAlchemy параметризует запросы; следить за сырыми SQL/`ilike` с пользовательским вводом. |

### 9.7 Предлагаемые улучшения (приоритеты)

1. 🔴 **Привести в соответствие уведомления**: реализовать `/api/notifications/*` + `/ws/notifications` ИЛИ убрать `notifications.js`/`notifications.css`.
2. 🔴 Удалить `server.py`; починить `migrations/env.py` (`target_metadata`); сгенерировать первую миграцию.
3. 🔴 Заменить `SECRET_KEY` и убрать дефолтного админа из прод-конфига; ужесточить CORS.
4. 🟠 Убрать неиспользуемые `passlib`/`redis` либо начать их использовать; добавить явный `bcrypt` в `requirements.txt`.
5. 🟠 Оптимизировать N+1 и dashboard-счётчики (`COUNT(*)`).
6. 🟠 Дополнить `.gitignore` (`.venv/`, `jobflow.db`, `.idea/`).
7. 🟡 Добавить тесты (pytest + httpx), CI/CD, логирование.
8. 🟡 Перевести чат на WebSocket (уже есть задел в `notifications.js`).
9. 🟢 Версионировать API (`/api/v1`), ввести интерфейсы репозиториев.

---

## 10. Раздел для нового разработчика

### 10.1 Что это за проект простыми словами

JobFlow — сайт для поиска работы. Соискатели создают резюме и откликаются на вакансии компаний. Работодатели публикуют вакансии и общаются с кандидатами в чате (чат создаётся автоматически при отклике). Есть администратор с панелью управления.

### 10.2 Что нужно установить

| Инструмент | Версия | Зачем |
|---|---|---|
| Python | 3.11+ (3.12 в Docker) | Запуск бэкенда |
| pip | latest | Установка зависимостей |
| Docker + Docker Compose | latest | Запуск через контейнеры (опционально) |
| Git | latest | Клонирование репозитория |
| Редактор | VS Code / PyCharm | Разработка |

### 10.3 Быстрый старт (локально, без Docker)

```bash
# 1. Клонировать проект
git clone <url-репозитория> SUMMER_PROJECT
cd SUMMER_PROJECT

# 2. Создать виртуальное окружение
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/macOS

# 3. Установить зависимости
pip install -r requirements.txt

# 4. Настроить окружение
#    Файл .env уже содержит дефолты (SQLite). Для безопасности
#    поменяйте SECRET_KEY. Для PostgreSQL — задайте DATABASE_URL.

# 5. Запустить сервер (таблицы создадутся автоматически в lifespan)
uvicorn app.main:app --reload --port 8000

# 6. Открыть в браузере
#    http://localhost:8000
```

### 10.4 Быстрый старт (через Docker)

```bash
docker-compose up --build
# Приложение (web):  http://localhost:8000
# PostgreSQL (db):   порт 5432
# Redis:             порт 6379
```

### 10.5 Учётная запись администратора (по умолчанию)

```
Email: admin@jobflow.ru
Пароль: admin123
```

> ⚠️ Только для разработки. В проде отключить автосоздание (`_create_admin` в `app/main.py`).

### 10.6 Как устроен проект (с чего начать чтение кода)

Рекомендуемый порядок изучения:

1. **`app/main.py`** — точка входа: сборка приложения, CORS, роуты статики, `include_router`.
2. **`app/core/config.py`** — какие настройки есть.
3. **`app/database/db.py`** — как подключается БД.
4. **`app/models/`** — структура таблиц (схема данных).
5. **`app/schemas/`** — какие данные принимает/отдаёт API.
6. **`app/repositories/repo.py`** — как ходим в БД.
7. **`app/services/`** — бизнес-логика (особенно `vacancy_service.apply_to_vacancy` и `chat_service`).
8. **`app/api/`** — HTTP-эндпоинты.
9. **`app/core/security.py` + `app/core/deps.py`** — авторизация.
10. **`html/` + `js/`** — фронтенд (`auth-guard.js`, `nav-auth.js`).

### 10.7 Куда что добавлять

| Хочу добавить... | Куда класть |
|---|---|
| Новый эндпоинт | `app/api/<domain>.py` |
| Новую таблицу | `app/models/<name>.py` + экспорт в `app/models/__init__.py` + импорт в `migrations/env.py` |
| Новую схему запроса/ответа | `app/schemas/<domain>.py` |
| Бизнес-правило | `app/services/<domain>_service.py` |
| Запрос к БД | `app/repositories/repo.py` (для чатов — `chat_service.py`) |
| Новую HTML-страницу | `html/<page>.html` (доступна автоматически как `/<page>.html`) |
| Стили | `css/<page>.css` (доступна как `/css/<page>.css`) |
| Общий JS | `js/<name>.js` (доступна как `/js/<name>.js`) |

### 10.8 Полезные команды

```bash
# Запуск с автоперезагрузкой
uvicorn app.main:app --reload

# Создать новую миграцию (после правок моделей)
alembic revision --autogenerate -m "описание"

# Применить миграции
alembic upgrade head

# Откатить последнюю миграцию
alembic downgrade -1

# Запустить тесты (когда появятся)
pytest
```

### 10.9 Частые грабли

- **«Колокольчик уведомлений пуст»** — это ожидаемо: бэкенда `/api/notifications/*` и `/ws/notifications` пока нет (см. 9.2).
- **«Таблица не создаётся»** — миграций нет, таблицы создаёт `create_all` в `lifespan`; убедитесь, что модель импортирована и доступна в `Base.metadata`.
- **«401 Unauthorized»** — токен истёк или не передан в заголовке `Authorization: Bearer ...`. `auth-guard.js` автоматически редиректит на `login.html`.
- **«403 на профиль»** — эндпоинты профилей защищены по роли (`/candidate/profile` — только candidate, `/employer/profile` — только employer).
- **«Не могу писать в чат»** — отправка блокируется, если отклик в статусе `rejected`.
- **«psycopg2 не ставится»** — нужен компилятор; используйте `psycopg2-binary` или Postgres в Docker.
- **«Static 404»** — проверьте, что файл реально лежит в `html/`/`css/`/`js/`; пути отдаются через `FileResponse`-роуты.

---

## Приложение А. Карта взаимодействий модулей

```
app/main.py
   ├── импортирует: app.database.db (Base, engine)
   ├── импортирует: app.core.config (settings)
   ├── подключает middleware: CORSMiddleware
   ├── mount: /static → app/static
   ├── FileResponse-роуты: /, /{name}.html, /css/*, /js/*
   ├── включает: app.api.auth.router      (prefix /api)
   ├── включает: app.api.users.router
   ├── включает: app.api.admin.router
   ├── включает: app.api.vacancies.router
   ├── включает: app.api.chat.router
   ├── включает: app.api.resumes.router
   └── включает: app.api.presence.router

app/api/*.py
   └── зависят от: app.services.*, app.core.deps, app.schemas.*, app.database.db

app/services/*.py
   ├── зависят от: app.repositories.repo, app.core.security, app.models.*
   └── chat_service содержит собственные ChatRepo/MessageRepo

app/repositories/repo.py
   └── зависят от: app.models.*, app.database.db

app/core/deps.py
   └── зависит от: app.core.security, app.repositories.repo

app/core/security.py
   └── зависит от: app.core.config, bcrypt, jose

Фронтенд (html/*.html)
   └── fetch -> /api/* (роутеры FastAPI)
   └── <link> -> /css/*.css
   └── <script> -> /js/*.js (auth-guard, nav-auth, city-loader, notifications)
```

---

## Приложение Б. Сводная таблица моделей БД

| Таблица | Поля (ключевые) | Связи |
|---|---|---|
| `users` | id, email (nullable, unique), phone (nullable, unique), password, role, created_at | → candidate, employer |
| `candidates` | id, user_id, name, surname, phone, city, skills, experience, education, resume | user_id → users |
| `employers` | id, user_id, company_name, website, description, phone, verified | user_id → users |
| `vacancies` | id, employer_id, title, description, salary, city, education, experience, employment_type, work_format, requirements, contact_phone, contact_email, status, created_at | employer_id → employers |
| `applications` | id, vacancy_id, candidate_id, status, created_at | vacancy_id, candidate_id |
| `chats` | id, application_id (unique), created_at | application_id → applications |
| `messages` | id, chat_id, sender_id, text, created_at | chat_id → chats, sender_id → users |
| `resumes` | id, candidate_id, title, position, salary, employment, city, education, skills, experience, about, languages, driving, status, created_at, updated_at | candidate_id → candidates |

---

*Документация актуализирована 2026-06-22 на основе анализа всех файлов проекта `SUMMER_PROJECT` (версия документа 2.0).*

import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.database.db import engine, Base
from app.api.auth import router as auth_router
from app.api.users import router as users_router
from app.api.admin import router as admin_router
from app.api.vacancies import router as vacancies_router
from app.api.chat import router as chat_router
from app.api.resumes import router as resumes_router
from app.api.presence import router as presence_router
from app.core.config import settings

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _create_admin()
    yield


def _create_admin():
    from sqlalchemy.orm import Session
    from app.models import User, RoleEnum
    from app.core.security import hash_password

    db = Session(bind=engine)
    try:
        existing = db.query(User).filter(User.email == "admin@jobflow.ru").first()
        if not existing:
            admin = User(
                email="admin@jobflow.ru",
                password=hash_password("admin123"),
                role=RoleEnum.admin,
            )
            db.add(admin)
            db.commit()
    finally:
        db.close()


app = FastAPI(title="JobFlow API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(vacancies_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(resumes_router, prefix="/api")
app.include_router(presence_router, prefix="/api")

app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "app", "static")), name="static")


@app.get("/")
def serve_index():
    return FileResponse(os.path.join(BASE_DIR, "html", "index.html"))


@app.get("/{name}.html")
def serve_page(name: str):
    return FileResponse(os.path.join(BASE_DIR, "html", f"{name}.html"))


@app.get("/css/{name}.css")
def serve_css(name: str):
    return FileResponse(os.path.join(BASE_DIR, "css", f"{name}.css"))


@app.get("/js/{name}.js")
def serve_js(name: str):
    return FileResponse(os.path.join(BASE_DIR, "js", f"{name}.js"))

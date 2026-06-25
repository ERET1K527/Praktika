from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.core.deps import get_current_user
from app.models import User
from app.services.presence_service import presence

router = APIRouter(prefix="/presence", tags=["Presence"])


@router.post("/heartbeat")
def api_heartbeat(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    presence.heartbeat(current_user.id)
    return {"detail": "ok"}


@router.get("/online")
def api_online(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"online": presence.online_user_ids(exclude=current_user.id)}

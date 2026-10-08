from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.security import treasury_identity
from app.api.production import invoke
from app.schemas.scheduled_updates import ScheduleSave
from app.services import scheduled_updates as service

router = APIRouter(prefix="/api/v1/scheduled-updates", tags=["Scheduled collection readiness"])


@router.get("")
def schedules(actor: str = Depends(treasury_identity), db: Session = Depends(get_db)):
    return invoke(db, service.list_schedules, actor)


@router.put("")
def save(request: ScheduleSave, actor: str = Depends(treasury_identity), db: Session = Depends(get_db)):
    return invoke(db, service.save_schedule, request, actor)

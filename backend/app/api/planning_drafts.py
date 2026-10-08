from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.security import treasury_identity
from app.api.production import invoke
from app.schemas.planning_drafts import PlanningDraftSave
from app.services import planning_drafts

router = APIRouter(prefix="/api/v1/company", tags=["Saved cash planning"])


@router.get("/planning-draft")
def read(actor: str = Depends(treasury_identity), db: Session = Depends(get_db)):
    return invoke(db, planning_drafts.read_draft, actor)


@router.put("/planning-draft")
def save(request: PlanningDraftSave, actor: str = Depends(treasury_identity), db: Session = Depends(get_db)):
    return invoke(db, planning_drafts.save_draft, request, actor)

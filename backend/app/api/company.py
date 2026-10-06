from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.security import treasury_identity
from app.api.production import invoke
from app.schemas.company import ProfileSave, EntityRegister
from app.services import company

router = APIRouter(prefix="/api/v1/company", tags=["Company setup"])


@router.get("/setup")
def setup(actor: str = Depends(treasury_identity), db: Session = Depends(get_db)):
    return invoke(db, company.setup, actor)


@router.post("/profile")
def profile(request: ProfileSave, actor: str = Depends(treasury_identity), db: Session = Depends(get_db)):
    return invoke(db, company.save_profile, request, actor)


@router.post("/entities")
def entities(request: EntityRegister, actor: str = Depends(treasury_identity), db: Session = Depends(get_db)):
    return invoke(db, company.register_entity, request, actor)

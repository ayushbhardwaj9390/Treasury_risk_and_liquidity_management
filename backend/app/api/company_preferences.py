from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.security import treasury_identity
from app.api.production import invoke
from app.schemas.company_preferences import PreferencesSave
from app.services import company_preferences

router = APIRouter(prefix="/api/v1/company-preferences", tags=["Company preference drafts"])


@router.get("")
def read(actor: str = Depends(treasury_identity), db: Session = Depends(get_db)):
    return invoke(db, company_preferences.read_preferences, actor)


@router.put("")
def save(request: PreferencesSave, actor: str = Depends(treasury_identity), db: Session = Depends(get_db)):
    return invoke(db, company_preferences.save_preferences, request, actor)

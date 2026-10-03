from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import treasury_identity
from app.models.production import ProductionEvent
from app.schemas.production import (
    ReleaseCreate, EvidenceCreate, SignoffCreate, ObservationCreate,
    TransitionCreate, BenchmarkCreate,
)
from app.services import production as service
from app.services.enterprise_controls import _user

router = APIRouter(prefix="/api/v1/production", tags=["Production governance"])


def invoke(db, fn, *args):
    try:
        return fn(db, *args)
    except PermissionError as exc:
        db.rollback()
        raise HTTPException(403, str(exc)) from exc
    except LookupError as exc:
        db.rollback()
        raise HTTPException(404, str(exc)) from exc
    except (ValueError, IntegrityError) as exc:
        db.rollback()
        raise HTTPException(409, "Duplicate or conflicting record" if isinstance(exc, IntegrityError) else str(exc)) from exc


@router.post("/releases")
def create(request: ReleaseCreate, actor: str = Depends(treasury_identity), db: Session = Depends(get_db)):
    return invoke(db, service.create_release, request, actor)


@router.get("/releases/{release_id}")
def gate(release_id: int, actor: str = Depends(treasury_identity), db: Session = Depends(get_db)):
    invoke(db, _user, actor)
    return invoke(db, service.snapshot, release_id)


@router.post("/releases/{release_id}/evidence")
def evidence(release_id: int, request: EvidenceCreate, actor: str = Depends(treasury_identity), db: Session = Depends(get_db)):
    return invoke(db, service.add_evidence, release_id, request, actor)


@router.post("/releases/{release_id}/observations")
def observation(release_id: int, request: ObservationCreate, actor: str = Depends(treasury_identity), db: Session = Depends(get_db)):
    return invoke(db, service.add_observation, release_id, request, actor)


@router.post("/releases/{release_id}/signoffs")
def signoff(release_id: int, request: SignoffCreate, actor: str = Depends(treasury_identity), db: Session = Depends(get_db)):
    return invoke(db, service.signoff, release_id, request, actor)


@router.post("/releases/{release_id}/transitions")
def transition(release_id: int, request: TransitionCreate, actor: str = Depends(treasury_identity), db: Session = Depends(get_db)):
    return invoke(db, service.transition, release_id, request, actor)


@router.get("/releases/{release_id}/events")
def events(release_id: int, actor: str = Depends(treasury_identity), db: Session = Depends(get_db)):
    invoke(db, _user, actor)
    invoke(db, service.release, release_id)
    return db.scalars(select(ProductionEvent).where(ProductionEvent.release_id == release_id).order_by(ProductionEvent.id)).all()


@router.post("/model-benchmark")
def benchmark(request: BenchmarkCreate, actor: str = Depends(treasury_identity), db: Session = Depends(get_db)):
    invoke(db, service.actor_role, actor, {"RISK_MANAGER"})
    try:
        return service.benchmark(request)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

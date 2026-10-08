from datetime import UTC, datetime
from sqlalchemy import update
from app.models import AuditLog
from app.models.company_preferences import CompanyPreferences
from app.services.enterprise_controls import _user
from app.services.production import actor_role


def read_preferences(db, actor):
    user = _user(db, actor)
    row = db.get(CompanyPreferences, 1)
    return {"can_edit": user.role == "GROUP_TREASURER", "status": "DRAFT_NOT_ACTIVATED",
        "draft": None if row is None else {**row.payload, "version": row.version,
            "updated_by": row.updated_by, "updated_at": row.updated_at.isoformat() + "Z"}}


def save_preferences(db, request, actor):
    actor_role(db, actor, {"GROUP_TREASURER"})
    payload = request.model_dump(exclude={"expected_version"})
    if request.expected_version == 0:
        db.add(CompanyPreferences(id=1, payload=payload, updated_by=actor))
    else:
        changed = db.execute(update(CompanyPreferences).where(CompanyPreferences.id == 1,
            CompanyPreferences.version == request.expected_version).values(payload=payload,
            version=request.expected_version + 1, updated_by=actor,
            updated_at=datetime.now(UTC).replace(tzinfo=None)))
        if changed.rowcount != 1:
            raise ValueError("Company preferences changed. Reload before saving.")
    db.add(AuditLog(event_type="COMPANY_PREFERENCES_SAVED", actor=actor,
        details=f"Company preference draft version {request.expected_version + 1}; no policy activation or role grants"))
    db.commit()
    return read_preferences(db, actor)

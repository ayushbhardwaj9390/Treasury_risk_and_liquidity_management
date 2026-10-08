from datetime import UTC, datetime
from sqlalchemy import update
from app.models import AuditLog
from app.models.planning_drafts import PlanningDraft
from app.services.enterprise_controls import _user
from app.services.production import actor_role


def read_draft(db, actor):
    user = _user(db, actor)
    row = db.get(PlanningDraft, 1)
    return {"can_edit": user.role == "GROUP_TREASURER", "draft": None if row is None else {
        **row.payload, "version": row.version, "updated_by": row.updated_by,
        "updated_at": row.updated_at.isoformat() + "Z"}}


def save_draft(db, request, actor):
    actor_role(db, actor, {"GROUP_TREASURER"})
    payload = request.model_dump(exclude={"expected_version"})
    if request.expected_version == 0:
        db.add(PlanningDraft(id=1, payload=payload, version=1, updated_by=actor))
    else:
        changed = db.execute(update(PlanningDraft).where(PlanningDraft.id == 1,
            PlanningDraft.version == request.expected_version).values(payload=payload,
            version=request.expected_version + 1, updated_by=actor,
            updated_at=datetime.now(UTC).replace(tzinfo=None)))
        if changed.rowcount != 1:
            raise ValueError("The saved plan changed. Reload it before saving again.")
    db.add(AuditLog(event_type="PLANNING_DRAFT_SAVED", actor=actor,
        details=f"Planning draft version {request.expected_version + 1}; {len(request.flows)} records; planning inputs only"))
    db.commit()
    return read_draft(db, actor)

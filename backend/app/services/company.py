from datetime import UTC, datetime
from sqlalchemy import select, update
from app.core.config import settings
from app.models import AuditLog, LegalEntity, UserAccount
from app.models.company import CompanyProfile, CompanyEntityRegistration
from app.services.enterprise_controls import _user
from app.services.production import actor_role


def setup(db, actor):
    user = _user(db, actor)
    profile = db.get(CompanyProfile, 1)
    return {
        "deployment_mode": "DEDICATED_COMPANY", "can_edit": user.role == "GROUP_TREASURER",
        "reporting_currency": settings.group_reporting_currency,
        "profile": None if profile is None else {"company_name": profile.company_name, "industry": profile.industry,
            "country_code": profile.country_code, "version": profile.version},
        "registrations": [{"id": e.id, "name": e.name, "country_code": e.country_code,
            "functional_currency": e.functional_currency, "status": "PENDING_REVIEW"}
            for e in db.scalars(select(CompanyEntityRegistration).order_by(CompanyEntityRegistration.id))],
        "entities": [{"id": e.id, "name": e.name, "country_code": e.country_code,
            "functional_currency": e.functional_currency, "active": e.active}
            for e in db.scalars(select(LegalEntity).order_by(LegalEntity.id))],
        "users": [{"display_name": u.display_name, "role": u.role} for u in
            db.scalars(select(UserAccount).where(UserAccount.active.is_(True)).order_by(UserAccount.id))],
    }


def save_profile(db, request, actor):
    actor_role(db, actor, {"GROUP_TREASURER"})
    values = {"company_name": request.company_name, "industry": request.industry, "country_code": request.country_code}
    if request.expected_version == 0:
        db.add(CompanyProfile(id=1, **values))
    else:
        changed = db.execute(update(CompanyProfile).where(CompanyProfile.id == 1,
            CompanyProfile.version == request.expected_version).values(**values,
            version=request.expected_version + 1, updated_at=datetime.now(UTC).replace(tzinfo=None)))
        if changed.rowcount != 1:
            raise ValueError("Company profile changed. Reload before saving.")
    db.add(AuditLog(event_type="COMPANY_PROFILE_SAVED", actor=actor,
        details=f"Company profile version {request.expected_version + 1}; setup metadata only"))
    db.commit()
    return setup(db, actor)


def register_entity(db, request, actor):
    actor_role(db, actor, {"GROUP_TREASURER"})
    if db.get(CompanyProfile, 1) is None:
        raise ValueError("Save the company profile first.")
    name_key = request.name.casefold()
    if any(e.name.casefold() == name_key for e in db.scalars(select(LegalEntity))):
        raise ValueError("This entity already exists in the treasury engine.")
    row = CompanyEntityRegistration(name=request.name, name_key=name_key, country_code=request.country_code,
        functional_currency=request.functional_currency, created_by=actor)
    db.add(row)
    db.flush()
    db.add(AuditLog(event_type="COMPANY_ENTITY_REGISTERED", actor=actor,
        details=f"Pending entity registration {row.id}; no engine activation"))
    db.commit()
    return setup(db, actor)

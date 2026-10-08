from contextlib import asynccontextmanager
import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy import text

from app.api.routes import router
from app.api.production import router as production_router
from app.api.company import router as company_router
from app.core.config import settings
from app.core.db import Base, SessionLocal, engine
from app.core.observability import Timer, observe_request, render_prometheus
from app.seed import seed_demo

logger = logging.getLogger("global_treasury_ai")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.environment.lower() == "production":
        if settings.auth_mode != "oidc_jwt" or not all((settings.oidc_issuer, settings.oidc_audience, settings.oidc_jwks_url)):
            raise RuntimeError("Production requires configured OIDC verification")
        if not settings.oidc_jwks_url.startswith("https://") or not settings.oidc_issuer.startswith("https://"):
            raise RuntimeError("Production identity endpoints require HTTPS")
        if "*" in settings.allowed_hosts or "*" in settings.cors_origins:
            raise RuntimeError("Wildcard production host/CORS configuration is forbidden")
        if settings.database_url.startswith("sqlite") or not settings.security_headers_enabled:
            raise RuntimeError("Production requires managed database and security headers")
    # Development convenience only. Production schema changes must use Alembic.
    if settings.environment.lower() != "production":
        Base.metadata.create_all(bind=engine)
        with SessionLocal() as db:
            seed_demo(db)
    yield


app = FastAPI(title=settings.app_name, version="0.10.0", lifespan=lifespan)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=[x.strip() for x in settings.allowed_hosts.split(",") if x.strip()])
app.add_middleware(
    CORSMiddleware,
    allow_origins=[x.strip() for x in settings.cors_origins.split(",") if x.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def response_headers(response, request_id):
    response.headers["X-Request-ID"] = request_id
    if settings.security_headers_enabled:
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none'"
        if settings.environment.lower() == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.middleware("http")
async def enterprise_request_controls(request: Request, call_next):
    request_id = str(uuid.uuid4())
    if request.url.path.startswith("/api/") and settings.environment.lower() == "production":
        from app.core.security import treasury_identity, connector_identity, CONNECTOR_INGESTION_PATHS
        from fastapi import HTTPException
        try:
            connector_type = CONNECTOR_INGESTION_PATHS.get(request.url.path) if request.method == "POST" else None
            if connector_type:
                actor = connector_identity(None, request.headers.get("Authorization"))
                from app.models import SourceConnector
                from sqlalchemy import select
                with SessionLocal() as db:
                    source = db.scalar(select(SourceConnector).where(SourceConnector.connector_name == actor,
                        SourceConnector.connector_type == connector_type, SourceConnector.status == "ACTIVE"))
                    if source is None:
                        raise PermissionError("Registered active connector required")
            else:
                actor = treasury_identity(None, request.headers.get("Authorization"))
                from app.services.enterprise_controls import _user
                with SessionLocal() as db:
                    _user(db, actor)
        except HTTPException as exc:
            return response_headers(JSONResponse(status_code=exc.status_code, content={"detail": exc.detail}), request_id)
        except PermissionError:
            return response_headers(JSONResponse(status_code=403, content={"detail": "Active authorized treasury account or registered connector required"}), request_id)
    if request.method in {"POST", "PUT", "PATCH"}:
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > settings.max_request_bytes:
                return response_headers(JSONResponse(status_code=413, content={"detail": "Request exceeds size limit"}), request_id)
        request._body = bytes(body)
    if (
        settings.environment.lower() == "production"
        and settings.production_write_idempotency_required
        and request.method in {"POST", "PUT", "PATCH"}
        and request.url.path.startswith("/api/v1/transactions/")
        and not request.headers.get("Idempotency-Key")
    ):
        return response_headers(JSONResponse(status_code=428, content={"detail": "Idempotency-Key required for production treasury write requests"}), request_id)
    with Timer() as timer:
        response = await call_next(request)
    response_headers(response, request_id)
    if settings.metrics_enabled:
        route = request.scope.get("route")
        observe_request(request.method, getattr(route, "path", "/unmatched"), response.status_code, timer.elapsed)
    logger.info("request_id=%s method=%s path=%s status=%s elapsed=%.4f", request_id, request.method, request.url.path, response.status_code, timer.elapsed)
    return response


@app.get("/health")
def health():
    return {"status": "ok", "service": settings.app_name, "version": app.version, "ai_model": settings.ai_model_label}


@app.get("/health/ready")
def readiness():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ready", "database": "ok"}
    except Exception:
        return JSONResponse(status_code=503, content={"status": "not_ready", "database": "error"})


@app.get("/health/production")
def production_readiness():
    from app.services.production import require_live_release
    try:
        with SessionLocal() as db:
            require_live_release(db)
        return {"status": "approved_live_release"}
    except Exception:
        return JSONResponse(status_code=503, content={"status": "blocked"})


@app.get("/metrics", response_class=PlainTextResponse)
def metrics():
    from app.services.production import snapshot
    ready = 0
    try:
        if settings.production_release_id:
            with SessionLocal() as db:
                gate = snapshot(db, settings.production_release_id)
                ready = int(gate["state"] == "LIVE" and gate["status"] == "READY")
    except Exception:
        logger.exception("Production monitoring could not evaluate release")
    return render_prometheus() + "# TYPE treasury_production_release_ready gauge\n" + f"treasury_production_release_ready {ready}\n"


app.include_router(router)
app.include_router(production_router)
app.include_router(company_router)

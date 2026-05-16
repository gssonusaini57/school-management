from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from .config import settings
from .db import SessionLocal
from .logging_config import configure_logging, get_logger
from .middleware import RequestContextMiddleware
from .routers import health, auth, students, files, attendance, marks, fees, notices, staff, reports, stream, pdf, pdf_templates, deletion_requests
from .routers.auth import _ensure_admin_seed, _ensure_super_admin_seed


configure_logging()
log = get_logger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("startup", extra={"event": "startup"})
    db = SessionLocal()
    try:
        _ensure_admin_seed(db)
        _ensure_super_admin_seed(db)
    finally:
        db.close()
    yield
    log.info("shutdown", extra={"event": "shutdown"})


app = FastAPI(title="KIS School Management API", version="1.0", lifespan=lifespan)

app.add_middleware(RequestContextMiddleware)

origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    log.exception(
        "unhandled exception",
        extra={
            "event": "unhandled_exception",
            "method": request.method,
            "path": request.url.path,
        },
    )
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

# pdf_templates MUST be registered BEFORE the legacy `pdf` router, because
# the legacy router matches `POST /pdf/{kind}` and would shadow `/pdf/templates`,
# `/pdf/cache/{id}`, etc. (FastAPI route resolution is first-match-wins.)
app.include_router(pdf_templates.router, prefix="/api")
app.include_router(pdf_templates.cache_router, prefix="/api")

api_routers = [health, auth, students, files, attendance, marks, fees, notices, staff, reports, stream, pdf, deletion_requests]
for r in api_routers:
    app.include_router(r.router, prefix="/api")


static_dir = Path(__file__).resolve().parent.parent.parent
index_path = static_dir / "index.html"
if index_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir / "static")), name="static")

    @app.get("/")
    def root():
        return FileResponse(str(index_path))

    @app.get("/index.html")
    def index_alias():
        return FileResponse(str(index_path))

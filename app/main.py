from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time

from app.config import get_settings
from app.routers import periodos, programas, unidades, docentes, alumnos, asignaciones, asistencias, me

settings = get_settings()

app = FastAPI(
    title="Sistema de Asistencia — API",
    description=(
        "Backend para registro de asistencia en instituto de educación superior tecnológico. "
        "Autenticación via Supabase Auth (JWT). "
        "Roles: **admin** (CRUD completo) y **docente** (registro de asistencia de sus unidades)."
    ),
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
)
app.router.redirect_slashes = True

# ── CORS ──────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Middleware de tiempo de respuesta ─────────────────────────
@app.middleware("http")
async def add_process_time(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = round((time.perf_counter() - start) * 1000, 2)
    response.headers["X-Process-Time-Ms"] = str(elapsed)
    return response

# ── Manejador global de errores no capturados ─────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": f"Error interno del servidor: {str(exc)}"},
    )

# ── Routers ───────────────────────────────────────────────────
PREFIX = "/api/v1"

app.include_router(periodos.router,    prefix=PREFIX)
app.include_router(programas.router,   prefix=PREFIX)
app.include_router(unidades.router,    prefix=PREFIX)
app.include_router(docentes.router,    prefix=PREFIX)
app.include_router(alumnos.router,     prefix=PREFIX)
app.include_router(asignaciones.router, prefix=PREFIX)
app.include_router(asistencias.router, prefix=PREFIX)
app.include_router(me.router,          prefix=PREFIX)

# ── Health check ──────────────────────────────────────────────
@app.get("/health", tags=["Health"])
def health():
    return {
        "status": "ok",
        "version": settings.app_version,
        "env": settings.app_env,
    }

@app.get("/", tags=["Health"])
def root():
    return {"message": "Sistema de Asistencia API", "docs": "/docs"}

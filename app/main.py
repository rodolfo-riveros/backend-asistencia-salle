from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time

from app.config import get_settings
from app.routers import periodos, programas, unidades, docentes, alumnos, asignaciones, asistencias, me, evaluaciones, gamificacion

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
    allow_credentials=False,
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
app.include_router(evaluaciones.router, prefix=PREFIX)
app.include_router(gamificacion.router, prefix=PREFIX)

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

@app.get("/debug/token", tags=["Debug"])
async def debug_token(request: Request):
    """Endpoint temporal para diagnosticar el JWT — ELIMINAR EN PRODUCCIÓN"""
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "").strip()
    
    if not token:
        return {"error": "No token provided"}
    
    try:
        # Solo decodifica SIN verificar firma
        from jose import jwt as jose_jwt
        header = jose_jwt.get_unverified_header(token)
        payload = jose_jwt.get_unverified_claims(token)
        
        # Intenta obtener JWKS
        import httpx
        settings = get_settings()
        jwks_url = f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"
        jwks_response = httpx.get(jwks_url, timeout=10)
        jwks_data = jwks_response.json()
        
        kid = header.get("kid")
        matching_key = next(
            (k for k in jwks_data.get("keys", []) if k.get("kid") == kid),
            None
        )
        
        return {
            "token_header": header,
            "token_algorithm": header.get("alg"),
            "token_kid": kid,
            "token_sub": payload.get("sub"),
            "token_role": payload.get("user_metadata", {}).get("role"),
            "token_exp": payload.get("exp"),
            "jwks_url": jwks_url,
            "jwks_status": jwks_response.status_code,
            "jwks_keys_count": len(jwks_data.get("keys", [])),
            "matching_key_found": matching_key is not None,
            "matching_key_alg": matching_key.get("alg") if matching_key else None,
        }
    except Exception as e:
        return {"error": str(e), "type": type(e).__name__}
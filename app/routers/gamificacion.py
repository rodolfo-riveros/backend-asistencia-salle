import random
import string
from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel

from app.auth import CurrentDocente
from app.database import get_client
from app.exceptions import bad_request, not_found, supabase_error
from app.schemas.evaluaciones import EvaluacionUpdate
import app.services.evaluaciones as eval_svc

router = APIRouter(prefix="/gamificacion", tags=["Gamificación"])

SES_TABLE  = "gamificacion_sesiones"
EVAL_TABLE = "evaluaciones"


# ── Schemas ───────────────────────────────────────────────────────────────────

class IniciarGamificacionPayload(BaseModel):
    evaluacion_id:      str
    configuracion_json: dict   # GamificationConfig: { strategy, questions[], criteria[] }


class IniciarGamificacionOut(BaseModel):
    sesion_id:     str
    room_code:     str          # código de 6 letras para compartir con alumnos
    evaluacion_id: str
    nombre:        str
    tipo:          str
    puntaje_maximo: int
    configuracion_json: dict
    estado:        str


class FinalizarPayload(BaseModel):
    """Payload para cerrar la sesión y guardar las notas."""
    notas: list[dict]   # [{alumno_id, aciertos, total_preguntas}]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _generar_room_code(length: int = 6) -> str:
    """Genera un código alfanumérico en mayúsculas. Ej: 'A3KZ9P'"""
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/sesion/", response_model=IniciarGamificacionOut, status_code=201)
def iniciar_gamificacion(payload: IniciarGamificacionPayload, _: CurrentDocente):
    """
    Paso final del Wizard de gamificación:
    1. Guarda configuracion_json (preguntas IA + strategy) en evaluaciones.
    2. Crea una fila en gamificacion_sesiones con un room_code único.
    3. Retorna el room_code para que el frontend llame createRoom() en Convex.
    """
    db = get_client()

    # 1. Guardar configuracion_json en la evaluación
    try:
        updated = eval_svc.update_evaluacion(
            db,
            payload.evaluacion_id,
            EvaluacionUpdate(configuracion_json=payload.configuracion_json),
        )
    except Exception as exc:
        raise supabase_error(exc)

    # 2. Generar room_code único
    max_intentos = 10
    room_code = None
    for _ in range(max_intentos):
        code = _generar_room_code()
        existing = (
            db.table(SES_TABLE)
            .select("id")
            .eq("room_code", code)
            .eq("estado", "lobby")
            .execute()
        )
        if not existing.data:
            room_code = code
            break

    if not room_code:
        raise bad_request("No se pudo generar un código único. Intenta de nuevo.")

    # 3. Insertar sesión en Supabase
    try:
        ses_res = db.table(SES_TABLE).insert({
            "evaluacion_id": payload.evaluacion_id,
            "room_code":     room_code,
            "estado":        "lobby",
        }).execute()

        if not ses_res.data:
            raise Exception("No se pudo crear la sesión")

        sesion = ses_res.data[0]
    except Exception as exc:
        raise supabase_error(exc)

    return IniciarGamificacionOut(
        sesion_id=         sesion["id"],
        room_code=         room_code,
        evaluacion_id=     str(updated.id),
        nombre=            updated.nombre,
        tipo=              updated.tipo,
        puntaje_maximo=    updated.puntaje_maximo,
        configuracion_json=updated.configuracion_json or {},
        estado=            "lobby",
    )


@router.get("/sesion/{evaluacion_id}/", status_code=200)
def get_sesion_activa(evaluacion_id: str, _: CurrentDocente):
    """Retorna la sesión activa (lobby o active) de una evaluación."""
    db = get_client()
    try:
        res = (
            db.table(SES_TABLE)
            .select("*")
            .eq("evaluacion_id", evaluacion_id)
            .in_("estado", ["lobby", "active"])
            .order("lanzado_el", desc=True)
            .limit(1)
            .execute()
        )
        if not res.data:
            raise not_found("Sesión activa", evaluacion_id)
        return res.data[0]
    except Exception as exc:
        raise supabase_error(exc)


@router.post("/sesion/{sesion_id}/finalizar/", status_code=200)
def finalizar_sesion(sesion_id: str, payload: FinalizarPayload, _: CurrentDocente):
    """
    Cierra la sesión en Supabase y guarda las notas del quiz.
    Llamar cuando Convex detecta status === 'finished'.
    """
    db = get_client()

    # Obtener la sesión para sacar evaluacion_id
    try:
        ses_res = db.table(SES_TABLE).select("*").eq("id", sesion_id).single().execute()
        if not ses_res.data:
            raise not_found("Sesión", sesion_id)
        sesion = ses_res.data
    except Exception as exc:
        raise supabase_error(exc)

    # Marcar como finalizada
    try:
        db.table(SES_TABLE).update({
            "estado":        "finished",
            "finalizado_el": datetime.now(timezone.utc).isoformat(),
        }).eq("id", sesion_id).execute()
    except Exception as exc:
        raise supabase_error(exc)

    # Guardar notas en calificaciones
    from app.schemas.evaluaciones import NotasGamificacionPayload
    resultado = eval_svc.bulk_notas_gamificacion(
        db,
        NotasGamificacionPayload(
            evaluacion_id=sesion["evaluacion_id"],
            notas=payload.notas,
        ),
    )

    return {
        "sesion_id":               sesion_id,
        "estado":                  "finished",
        "calificaciones_guardadas": resultado.get("guardadas", 0),
    }


@router.get("/sesiones/{evaluacion_id}/historial/", status_code=200)
def historial_sesiones(evaluacion_id: str, _: CurrentDocente):
    """Lista el historial de todas las sesiones de una evaluación."""
    db = get_client()
    try:
        res = (
            db.table(SES_TABLE)
            .select("*")
            .eq("evaluacion_id", evaluacion_id)
            .order("lanzado_el", desc=True)
            .execute()
        )
        return res.data
    except Exception as exc:
        raise supabase_error(exc)

from fastapi import APIRouter
from app.auth import CurrentDocente, CurrentUser, CurrentAdmin
from app.database import get_client
from app.schemas.evaluaciones import (
    IndicadorCreate, IndicadorUpdate, IndicadorOut,
    ConfigEvaluacionPayload, ConfigEvaluacionOut,
    EvaluacionCreate, EvaluacionUpdate, EvaluacionOut,
    GruposPayload, GrupoCreate, GrupoOut,
    CalificacionCreate, CalificacionOut,
    NotasGamificacionPayload,
    SaveAllPayload, RegistroAuxiliarOut,
)
import app.services.evaluaciones as svc
from app.services.evaluaciones import EvaluacionUpdate  # usado en iniciar-sala

router = APIRouter(prefix="/evaluaciones", tags=["Evaluaciones"])


# ── POST /evaluaciones/config/ ─────────────────────────────────────────────────
# Paso 1 + Paso 2/3: upsert indicador + insert evaluación en una sola llamada

@router.post("/config/", response_model=ConfigEvaluacionOut, status_code=201)
def crear_config_evaluacion(data: ConfigEvaluacionPayload, _: CurrentDocente):
    """
    Recibe los datos del Paso 1 (Indicador) y Paso 2/3 (Instrumento).
    1. Hace upsert en `indicadores_logro` usando (unidad_id, periodo_id, codigo).
    2. Inserta la evaluación vinculada al indicador.
    3. Publica los criterios en Firebase para que el frontend los use en gamificación.
    """
    return svc.upsert_config_evaluacion(get_client(), data)


# ── GET /evaluaciones/config/{unidad_id}/{periodo_id} ──────────────────────────
# Estado completo: JOIN evaluaciones + indicadores_logro + grupos + notas

@router.get("/config/{unidad_id}/{periodo_id}", response_model=RegistroAuxiliarOut)
def get_config(unidad_id: str, periodo_id: str, _: CurrentDocente):
    """
    Carga todas las evaluaciones configuradas para el registro auxiliar y el selector de Quizz.
    Hace JOIN entre `evaluaciones` e `indicadores_logro`.
    """
    return svc.get_registro_auxiliar(get_client(), unidad_id, periodo_id)


# ── POST /evaluaciones/calificar/ ──────────────────────────────────────────────
# Guardar nota individual (manual o digitalización)

@router.post("/calificar/", response_model=list[CalificacionOut], status_code=201)
def calificar(data: CalificacionCreate, _: CurrentDocente):
    """
    Guarda la nota de un alumno (Paso manual o por digitalización de instrumento).
    - Si es GRUPAL: replica la nota a todos los integrantes del equipo.
    - Si es QUIZZ: calcula la nota desde detalles_json.aciertos / total_preguntas.
    Hace upsert en `calificaciones`.
    """
    return svc.upsert_calificacion(get_client(), data)


# ── POST /evaluaciones/notas-gamificacion/ ─────────────────────────────────────
# Bulk insert al finalizar el Quizz en vivo

@router.post("/notas-gamificacion/", status_code=200)
def notas_gamificacion(payload: NotasGamificacionPayload, _: CurrentDocente):
    """
    Sincronización masiva al terminar un Quizz.
    Recibe un array de notas [{alumno_id, aciertos, total_preguntas}]
    y hace bulk upsert en `calificaciones`.
    """
    return svc.bulk_notas_gamificacion(get_client(), payload)


# ── POST /evaluaciones/grupos/ ─────────────────────────────────────────────────
# Paso 4: conformación de equipos

@router.post("/grupos/", response_model=list[GrupoOut], status_code=201)
def guardar_grupos(payload: GruposPayload, _: CurrentDocente):
    """
    Guarda la conformación de equipos del Paso 4.
    Inserta en `evaluacion_grupos` y sus respectivos integrantes.
    Es idempotente: si ya existen grupos para esa evaluación, los reemplaza.
    """
    return svc.guardar_grupos(get_client(), payload)


# ── Indicadores CRUD ───────────────────────────────────────────────────────────

@router.post("/indicadores/", response_model=IndicadorOut, status_code=201)
def create_indicador(data: IndicadorCreate, _: CurrentDocente):
    return svc.create_indicador(get_client(), data)


@router.get("/indicadores/{unidad_id}/{periodo_id}", response_model=list[IndicadorOut])
def list_indicadores(unidad_id: str, periodo_id: str, _: CurrentUser):
    return svc.list_indicadores(get_client(), unidad_id, periodo_id)


@router.patch("/indicadores/{id}", response_model=IndicadorOut)
def update_indicador(id: str, data: IndicadorUpdate, _: CurrentDocente):
    return svc.update_indicador(get_client(), id, data)


@router.delete("/indicadores/{id}", status_code=204)
def delete_indicador(id: str, _: CurrentAdmin):
    svc.delete_indicador(get_client(), id)


# ── Evaluaciones CRUD ──────────────────────────────────────────────────────────

@router.post("/", response_model=EvaluacionOut, status_code=201)
def create_evaluacion(data: EvaluacionCreate, _: CurrentDocente):
    return svc.create_evaluacion(get_client(), data)


@router.get("/{id}", response_model=EvaluacionOut)
def get_evaluacion(id: str, _: CurrentUser):
    return svc.get_evaluacion(get_client(), id)


@router.get("/by-indicador/{indicador_id}", response_model=list[EvaluacionOut])
def list_evaluaciones(indicador_id: str, _: CurrentUser):
    return svc.list_evaluaciones(get_client(), indicador_id)


@router.patch("/{id}", response_model=EvaluacionOut)
def update_evaluacion(id: str, data: EvaluacionUpdate, _: CurrentDocente):
    return svc.update_evaluacion(get_client(), id, data)


@router.delete("/{id}", status_code=204)
def delete_evaluacion(id: str, _: CurrentAdmin):
    svc.delete_evaluacion(get_client(), id)


# ── Grupos ─────────────────────────────────────────────────────────────────────

@router.get("/grupos/{evaluacion_id}", response_model=list[GrupoOut])
def list_grupos(evaluacion_id: str, _: CurrentUser):
    return svc.list_grupos(get_client(), evaluacion_id)


@router.post("/grupos/{grupo_id}/integrantes/{alumno_id}", status_code=201)
def add_integrante(grupo_id: str, alumno_id: str, _: CurrentDocente):
    svc.add_integrante(get_client(), grupo_id, alumno_id)
    return {"ok": True}


# ── Calificaciones ─────────────────────────────────────────────────────────────

@router.get("/calificaciones/{evaluacion_id}", response_model=list[CalificacionOut])
def list_calificaciones(evaluacion_id: str, _: CurrentUser):
    return svc.list_calificaciones(get_client(), evaluacion_id)


@router.get("/calificaciones/detalle/{id}", response_model=CalificacionOut)
def get_calificacion(id: str, _: CurrentUser):
    return svc.get_calificacion(get_client(), id)


# ── Save-all (legacy) ──────────────────────────────────────────────────────────

@router.post("/save-all/", status_code=200)
def save_all(payload: SaveAllPayload, _: CurrentDocente):
    return svc.save_all(get_client(), payload)

# ── POST /evaluaciones/{id}/iniciar-sala/ ──────────────────────────────────────
# Guarda configuracion_json (preguntas IA) + retorna datos para que el frontend
# cree la sala en Convex automáticamente

from pydantic import BaseModel as _BaseModel

class IniciarSalaPayload(_BaseModel):
    configuracion_json: dict  # GamificationConfig con questions[], criteria[], strategy


class IniciarSalaOut(_BaseModel):
    evaluacion_id: str
    nombre:        str
    tipo:          str
    puntaje_maximo: int
    configuracion_json: dict


@router.post("/{id}/iniciar-sala/", response_model=IniciarSalaOut, status_code=200)
def iniciar_sala(id: str, payload: IniciarSalaPayload, _: CurrentDocente):
    """
    Paso final del Wizard de gamificación:
    1. Guarda el configuracion_json (preguntas generadas por IA + strategy) en Supabase.
    2. Retorna los datos que el frontend necesita para llamar rooms:createRoom en Convex.
    El frontend hace ambas cosas: llama este endpoint y luego crea la sala en Convex.
    """
    db = get_client()
    updated = svc.update_evaluacion(db, id, svc.EvaluacionUpdate(
        configuracion_json=payload.configuracion_json
    ))
    return IniciarSalaOut(
        evaluacion_id=str(updated.id),
        nombre=updated.nombre,
        tipo=updated.tipo,
        puntaje_maximo=updated.puntaje_maximo,
        configuracion_json=updated.configuracion_json or {},
    )

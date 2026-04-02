from datetime import date
from fastapi import APIRouter, Query
from app.auth import CurrentDocente, CurrentUser
from app.database import get_client
from app.schemas import (
    AsistenciaOut, AsistenciaUpdate, AsistenciaUpsert,
    AsistenciaDetalle, ResumenAsistencia,
)
import app.services.asistencias as svc

router = APIRouter(prefix="/asistencias", tags=["Asistencias"])


# ── Registro de asistencia ────────────────────────────────────

@router.post("/pase-lista", response_model=list[AsistenciaOut], status_code=201)
def pase_de_lista(data: AsistenciaUpsert, docente: CurrentDocente):
    """
    Registra o actualiza el pase de lista completo de una unidad.
    Enviar la lista de todos los alumnos con su estado en una sola llamada.

    Estados válidos: P (Presente), F (Falta), J (Justificado), T (Tarde)
    """
    return svc.registrar_asistencia_bulk(get_client(), data, docente.sub)


@router.patch("/{id}", response_model=AsistenciaOut)
def corregir_asistencia(id: str, data: AsistenciaUpdate, docente: CurrentDocente):
    """Corrige el estado de un registro individual. Solo el docente que lo creó puede editarlo."""
    return svc.update_asistencia(get_client(), id, data, docente.sub)


@router.get("/{id}", response_model=AsistenciaOut)
def obtener_asistencia(id: str, _: CurrentUser):
    return svc.get_asistencia(get_client(), id)


# ── Reportes ──────────────────────────────────────────────────

@router.get("/reporte/unidad/{unidad_id}", response_model=list[AsistenciaDetalle])
def reporte_por_unidad(
    unidad_id:    str,
    _:            CurrentUser,
    fecha_inicio: date | None = Query(None, description="Ej: 2025-03-01"),
    fecha_fin:    date | None = Query(None, description="Ej: 2025-07-31"),
):
    """Lista detallada de todas las asistencias de una unidad, con filtro de fechas opcional."""
    return svc.reporte_por_unidad(get_client(), unidad_id, fecha_inicio, fecha_fin)


@router.get("/reporte/resumen/{unidad_id}", response_model=list[ResumenAsistencia])
def resumen_por_alumno(
    unidad_id:    str,
    _:            CurrentUser,
    fecha_inicio: date | None = Query(None),
    fecha_fin:    date | None = Query(None),
):
    """
    Resumen de asistencia por alumno: totales de P/F/J/T y porcentaje de asistencia.
    Considera P, T y J como asistidos para el cálculo del porcentaje.
    """
    return svc.resumen_por_alumno(get_client(), unidad_id, fecha_inicio, fecha_fin)

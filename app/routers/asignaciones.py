from fastapi import APIRouter, Query
from app.auth import CurrentAdmin, CurrentUser
from app.database import get_admin_client, get_client
from app.schemas import AsignacionCreate, AsignacionOut, AsignacionDetalle
import app.services.asistencias as svc

router = APIRouter(prefix="/asignaciones", tags=["Asignación Docente"])


@router.get("/", response_model=list[AsignacionDetalle])
def listar_asignaciones(
    _: CurrentUser,
    docente_id: str | None = Query(None),
    periodo:    str | None = Query(None, description="Ej: 2025-I"),
):
    return svc.list_asignaciones(get_client(), docente_id, periodo)


@router.get("/{id}", response_model=AsignacionDetalle)
def obtener_asignacion(id: str, _: CurrentUser):
    return svc.get_asignacion(get_client(), id)


@router.post("/", response_model=AsignacionOut, status_code=201)
def crear_asignacion(data: AsignacionCreate, _: CurrentAdmin):
    return svc.create_asignacion(get_admin_client(), data)


@router.delete("/{id}", status_code=204)
def eliminar_asignacion(id: str, _: CurrentAdmin):
    svc.delete_asignacion(get_admin_client(), id)

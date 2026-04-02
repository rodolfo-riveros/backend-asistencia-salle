from fastapi import APIRouter, Query
from app.auth import CurrentAdmin, CurrentUser
from app.database import get_admin_client, get_client
from app.schemas import AlumnoCreate, AlumnoUpdate, AlumnoOut, AlumnoConPrograma
import app.services.alumnos as svc

router = APIRouter(prefix="/alumnos", tags=["Alumnos"])


@router.get("/", response_model=list[AlumnoConPrograma])
def listar_alumnos(
    _: CurrentUser,
    programa_id: str | None = Query(None),
    semestre:    str | None = Query(None),
    search:      str | None = Query(None, description="Buscar por nombre"),
):
    return svc.list_alumnos(get_client(), programa_id, semestre, search)


@router.get("/dni/{dni}", response_model=AlumnoConPrograma)
def buscar_por_dni(dni: str, _: CurrentUser):
    return svc.get_alumno_by_dni(get_client(), dni)


@router.get("/{id}", response_model=AlumnoConPrograma)
def obtener_alumno(id: str, _: CurrentUser):
    return svc.get_alumno(get_client(), id)


@router.post("/", response_model=AlumnoOut, status_code=201)
def crear_alumno(data: AlumnoCreate, _: CurrentAdmin):
    return svc.create_alumno(get_admin_client(), data)


@router.patch("/{id}", response_model=AlumnoOut)
def actualizar_alumno(id: str, data: AlumnoUpdate, _: CurrentAdmin):
    return svc.update_alumno(get_admin_client(), id, data)


@router.delete("/{id}", status_code=204)
def eliminar_alumno(id: str, _: CurrentAdmin):
    svc.delete_alumno(get_admin_client(), id)

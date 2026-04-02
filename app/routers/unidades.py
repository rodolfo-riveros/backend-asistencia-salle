from fastapi import APIRouter, Query
from app.auth import CurrentAdmin, CurrentUser
from app.database import get_admin_client, get_client
from app.schemas import UnidadCreate, UnidadUpdate, UnidadOut, UnidadConPrograma
from app.schemas import AlumnoConPrograma
import app.services.unidades as svc
import app.services.alumnos as alumnos_svc

router = APIRouter(prefix="/unidades", tags=["Unidades Didácticas"])


@router.get("/", response_model=list[UnidadConPrograma])
def listar_unidades(
    _: CurrentUser,
    programa_id: str | None = Query(None),
    semestre:    str | None = Query(None),
):
    return svc.list_unidades(get_client(), programa_id, semestre)


@router.get("/{id}", response_model=UnidadConPrograma)
def obtener_unidad(id: str, _: CurrentUser):
    return svc.get_unidad(get_client(), id)


@router.get("/{id}/alumnos", response_model=list[AlumnoConPrograma])
def alumnos_de_unidad(id: str, _: CurrentUser):
    """Lista todos los alumnos que corresponden a esta unidad (programa + semestre)."""
    return alumnos_svc.list_alumnos_por_unidad(get_client(), id)


@router.post("/", response_model=UnidadOut, status_code=201)
def crear_unidad(data: UnidadCreate, _: CurrentAdmin):
    return svc.create_unidad(get_admin_client(), data)


@router.patch("/{id}", response_model=UnidadOut)
def actualizar_unidad(id: str, data: UnidadUpdate, _: CurrentAdmin):
    return svc.update_unidad(get_admin_client(), id, data)


@router.delete("/{id}", status_code=204)
def eliminar_unidad(id: str, _: CurrentAdmin):
    svc.delete_unidad(get_admin_client(), id)

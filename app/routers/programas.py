from fastapi import APIRouter
from app.auth import CurrentAdmin, CurrentUser
from app.database import get_admin_client, get_client
from app.schemas import ProgramaCreate, ProgramaUpdate, ProgramaOut
import app.services.programas as svc

router = APIRouter(prefix="/programas", tags=["Programas de Estudio"])


@router.get("/", response_model=list[ProgramaOut])
def listar_programas(_: CurrentUser):
    return svc.list_programas(get_client())


@router.get("/{id}", response_model=ProgramaOut)
def obtener_programa(id: str, _: CurrentUser):
    return svc.get_programa(get_client(), id)


@router.post("/", response_model=ProgramaOut, status_code=201)
def crear_programa(data: ProgramaCreate, _: CurrentAdmin):
    return svc.create_programa(get_admin_client(), data)


@router.patch("/{id}", response_model=ProgramaOut)
def actualizar_programa(id: str, data: ProgramaUpdate, _: CurrentAdmin):
    return svc.update_programa(get_admin_client(), id, data)


@router.delete("/{id}", status_code=204)
def eliminar_programa(id: str, _: CurrentAdmin):
    svc.delete_programa(get_admin_client(), id)

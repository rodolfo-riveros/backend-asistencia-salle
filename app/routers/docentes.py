from fastapi import APIRouter, Query
from app.auth import CurrentAdmin, CurrentUser
from app.database import get_admin_client, get_client
from app.schemas import DocenteCreate, DocenteUpdate, DocenteOut
import app.services.docentes as svc

router = APIRouter(prefix="/docentes", tags=["Docentes"])


@router.get("/", response_model=list[DocenteOut])
def listar_docentes(
    _: CurrentUser,
    es_transversal: bool | None = Query(None),
):
    return svc.list_docentes(get_client(), es_transversal)


@router.get("/{id}", response_model=DocenteOut)
def obtener_docente(id: str, _: CurrentUser):
    return svc.get_docente(get_client(), id)


@router.post("/", response_model=DocenteOut, status_code=201)
def crear_docente(data: DocenteCreate, _: CurrentAdmin):
    """
    Crea el perfil del docente. El 'id' debe ser el UUID del usuario
    previamente creado en Supabase Auth.
    """
    return svc.create_docente(get_admin_client(), data)


@router.patch("/{id}", response_model=DocenteOut)
def actualizar_docente(id: str, data: DocenteUpdate, _: CurrentAdmin):
    return svc.update_docente(get_admin_client(), id, data)


@router.delete("/{id}", status_code=204)
def eliminar_docente(id: str, _: CurrentAdmin):
    svc.delete_docente(get_admin_client(), id)

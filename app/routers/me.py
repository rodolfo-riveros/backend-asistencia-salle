from fastapi import APIRouter
from app.auth import CurrentDocente
from app.database import get_client
from app.schemas import DocenteOut, AsignacionDetalle, AlumnoConPrograma
import app.services.docentes as docentes_svc
import app.services.asistencias as asig_svc
import app.services.alumnos as alumnos_svc

router = APIRouter(prefix="/me", tags=["Mi Perfil (Docente)"])


@router.get("/perfil", response_model=DocenteOut)
def mi_perfil(docente: CurrentDocente):
    """Devuelve el perfil del docente autenticado."""
    return docentes_svc.get_docente(get_client(), docente.sub)


@router.get("/asignaciones", response_model=list[AsignacionDetalle])
def mis_asignaciones(
    docente: CurrentDocente,
    periodo: str | None = None,
):
    """Lista las unidades asignadas al docente autenticado, opcionalmente filtradas por periodo."""
    return asig_svc.list_asignaciones(get_client(), docente.sub, periodo)


@router.get("/unidades/{unidad_id}/alumnos", response_model=list[AlumnoConPrograma])
def alumnos_de_mi_unidad(unidad_id: str, _: CurrentDocente):
    """
    Lista los alumnos de una unidad asignada al docente.
    La RLS de Supabase garantiza que solo vea sus unidades.
    """
    return alumnos_svc.list_alumnos_por_unidad(get_client(), unidad_id)

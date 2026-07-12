from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from app.auth import CurrentAdmin, CurrentDocente
from app.database import get_admin_client, get_client
from app.schemas.recuperaciones import (
    RecEstudianteCreate, RecEstudianteUpdate, RecEstudianteOut,
    RecMatriculaCreate, RecMatriculaUpdate, RecMatriculaOut,
    RecEvaluacionCreate, RecEvaluacionOut,
    RecQuizGuardarRequest, RecQuizPreguntasOut, RecQuizEvaluarRequest,
)
import app.services.recuperaciones as svc
import app.services.nvidia as nvidia_svc
import app.services.gemini as gemini_svc


class GenerarPreguntasRequest(BaseModel):
    texto_markdown: str
    cantidad: int = Field(default=5, ge=1, le=20)


class GenerarPreguntasResponse(BaseModel):
    preguntas: list[dict]
    fuente: str  # "genkit" | "nvidia"

router = APIRouter(prefix="/recuperaciones", tags=["Recuperaciones"])


# ── Estudiantes ────────────────────────────────────────────────

@router.get("/estudiantes", response_model=list[RecEstudianteOut])
def listar_estudiantes(
    _: CurrentDocente,
    search: str | None = Query(None),
    programa: str | None = Query(None),
):
    return svc.list_estudiantes(get_client(), search, programa)


@router.post("/estudiantes", response_model=RecEstudianteOut, status_code=201)
def crear_estudiante(data: RecEstudianteCreate, _: CurrentAdmin):
    return svc.create_estudiante(get_admin_client(), data)


@router.patch("/estudiantes/{id}", response_model=RecEstudianteOut)
def actualizar_estudiante(id: str, data: RecEstudianteUpdate, _: CurrentAdmin):
    return svc.update_estudiante(get_admin_client(), id, data)


# ── Matrículas ─────────────────────────────────────────────────

@router.get("/matriculas", response_model=list[RecMatriculaOut])
def listar_matriculas(
    _: CurrentDocente,
    docente_id: str | None = Query(None),
    periodo: str | None = Query(None),
    estado: str | None = Query(None),
    search: str | None = Query(None),
):
    return svc.list_matriculas(get_client(), docente_id, periodo, estado, search)


@router.post("/matriculas", response_model=RecMatriculaOut, status_code=201)
def crear_matricula(data: RecMatriculaCreate, _: CurrentAdmin):
    return svc.create_matricula(get_admin_client(), data)


@router.patch("/matriculas/{id}", response_model=RecMatriculaOut)
def actualizar_matricula(id: str, data: RecMatriculaUpdate, _: CurrentAdmin):
    return svc.update_matricula(get_admin_client(), id, data)


@router.delete("/matriculas/{id}", status_code=204)
def eliminar_matricula(id: str, _: CurrentAdmin):
    svc.delete_matricula(get_admin_client(), id)


# ── Evaluaciones ───────────────────────────────────────────────

@router.get("/matriculas/{matricula_id}/evaluaciones", response_model=list[RecEvaluacionOut])
def listar_evaluaciones(matricula_id: str, _: CurrentDocente):
    return svc.list_evaluaciones(get_client(), matricula_id)


@router.post("/evaluaciones", response_model=RecEvaluacionOut, status_code=201)
def crear_evaluacion(data: RecEvaluacionCreate, _: CurrentDocente):
    return svc.create_evaluacion(get_admin_client(), data)


@router.delete("/evaluaciones/{id}", status_code=204)
def eliminar_evaluacion(id: str, _: CurrentDocente):
    svc.delete_evaluacion(get_admin_client(), id)


@router.post("/quiz", response_model=RecQuizPreguntasOut, status_code=201)
def guardar_quiz(data: RecQuizGuardarRequest, _: CurrentDocente):
    """Guarda las preguntas generadas por IA como un quiz de recuperación."""
    return svc.create_quiz(get_admin_client(), data)


@router.get("/matriculas/{matricula_id}/quizzes", response_model=list[RecQuizPreguntasOut])
def listar_quizzes(matricula_id: str, _: CurrentDocente):
    """Lista todos los quizzes de una matrícula."""
    return svc.list_quizzes(get_client(), matricula_id)


@router.get("/matriculas/{matricula_id}/quiz", response_model=RecQuizPreguntasOut | None)
def obtener_quiz_activo(matricula_id: str, _: CurrentDocente):
    """Obtiene el quiz activo (pendiente) de una matrícula."""
    return svc.get_quiz_activo(get_client(), matricula_id)


@router.get("/quiz/{quiz_id}", response_model=RecQuizPreguntasOut)
def obtener_quiz(quiz_id: str, _: CurrentDocente):
    return svc.get_quiz(get_client(), quiz_id)


@router.post("/quiz/{quiz_id}/evaluar")
def evaluar_quiz(quiz_id: str, data: RecQuizEvaluarRequest, _: CurrentDocente):
    """Evalúa las respuestas del estudiante y crea la evaluación automáticamente."""
    return svc.evaluar_quiz(get_admin_client(), quiz_id, data.respuestas)


@router.post("/evaluaciones/generar-preguntas", response_model=GenerarPreguntasResponse)
async def generar_preguntas(data: GenerarPreguntasRequest, _: CurrentDocente):
    """Intenta NVIDIA DeepSeek primero, luego cae a Gemini directo."""
    try:
        preguntas = await nvidia_svc.generar_preguntas_desde_texto(
            data.texto_markdown, data.cantidad
        )
        return GenerarPreguntasResponse(preguntas=preguntas, fuente="nvidia")
    except Exception:
        preguntas = await gemini_svc.generar_preguntas_desde_texto(
            data.texto_markdown, data.cantidad
        )
        return GenerarPreguntasResponse(preguntas=preguntas, fuente="gemini")


@router.post("/evaluaciones/generar-preguntas-forzar-gemini", response_model=GenerarPreguntasResponse)
async def generar_preguntas_forzar_gemini(data: GenerarPreguntasRequest, _: CurrentDocente):
    """Usa Gemini directo, saltando NVIDIA."""
    preguntas = await gemini_svc.generar_preguntas_desde_texto(
        data.texto_markdown, data.cantidad
    )
    return GenerarPreguntasResponse(preguntas=preguntas, fuente="gemini")

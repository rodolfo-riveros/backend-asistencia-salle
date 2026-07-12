from supabase import Client
from app.schemas.recuperaciones import (
    RecEstudianteCreate, RecEstudianteUpdate, RecEstudianteOut,
    RecMatriculaCreate, RecMatriculaUpdate, RecMatriculaOut,
    RecEvaluacionCreate, RecEvaluacionOut,
    RecQuizGuardarRequest, RecQuizPreguntasOut,
)
from app.exceptions import not_found, supabase_error

EST_TABLE = "rec_estudiantes"
MAT_TABLE = "rec_matriculas"
EVAL_TABLE = "rec_evaluaciones"


# ── Estudiantes ────────────────────────────────────────────────

def list_estudiantes(
    db: Client,
    search: str | None = None,
    programa: str | None = None,
) -> list[RecEstudianteOut]:
    try:
        q = db.table(EST_TABLE).select("*").order("nombre")
        if search:
            q = q.ilike("nombre", f"%{search}%")
        if programa:
            q = q.ilike("programa", f"%{programa}%")
        res = q.execute()
        return [RecEstudianteOut(**r) for r in res.data]
    except Exception as exc:
        raise supabase_error(exc)


def create_estudiante(db: Client, data: RecEstudianteCreate) -> RecEstudianteOut:
    try:
        payload = data.model_dump()
        res = db.table(EST_TABLE).insert(payload).execute()
        return RecEstudianteOut(**res.data[0])
    except Exception as exc:
        raise supabase_error(exc)


def update_estudiante(db: Client, id: str, data: RecEstudianteUpdate) -> RecEstudianteOut:
    payload = data.model_dump(exclude_none=True)
    if not payload:
        return get_estudiante(db, id)
    try:
        res = db.table(EST_TABLE).update(payload).eq("id", id).execute()
        if not res.data:
            raise not_found("Estudiante recuperación", id)
        return RecEstudianteOut(**res.data[0])
    except Exception as exc:
        raise supabase_error(exc)


def get_estudiante(db: Client, id: str) -> RecEstudianteOut:
    try:
        res = db.table(EST_TABLE).select("*").eq("id", id).single().execute()
        if not res.data:
            raise not_found("Estudiante recuperación", id)
        return RecEstudianteOut(**res.data)
    except Exception as exc:
        if "0 rows" in str(exc) or "not found" in str(exc).lower():
            raise not_found("Estudiante recuperación", id)
        raise supabase_error(exc)


# ── Matrículas ─────────────────────────────────────────────────

def list_matriculas(
    db: Client,
    docente_id: str | None = None,
    periodo: str | None = None,
    estado: str | None = None,
    search: str | None = None,
) -> list[RecMatriculaOut]:
    try:
        q = db.table(MAT_TABLE).select("*").order("created_at", desc=True)
        if docente_id:
            q = q.eq("docente_id", docente_id)
        if periodo:
            q = q.eq("periodo", periodo)
        if estado:
            q = q.eq("estado", estado)
        if search:
            q = q.ilike("estudiante_nombre", f"%{search}%")
        res = q.execute()
        return [RecMatriculaOut(**r) for r in res.data]
    except Exception as exc:
        raise supabase_error(exc)


def create_matricula(db: Client, data: RecMatriculaCreate) -> RecMatriculaOut:
    try:
        payload = data.model_dump()
        res = db.table(MAT_TABLE).insert(payload).execute()
        return RecMatriculaOut(**res.data[0])
    except Exception as exc:
        raise supabase_error(exc)


def update_matricula(db: Client, id: str, data: RecMatriculaUpdate) -> RecMatriculaOut:
    try:
        payload = data.model_dump(exclude_none=True)
        if not payload:
            res = db.table(MAT_TABLE).select("*").eq("id", id).single().execute()
            if not res.data:
                raise not_found("Matrícula recuperación", id)
            return RecMatriculaOut(**res.data)
        res = db.table(MAT_TABLE).update(payload).eq("id", id).execute()
        if not res.data:
            raise not_found("Matrícula recuperación", id)
        return RecMatriculaOut(**res.data[0])
    except Exception as exc:
        raise supabase_error(exc)


def delete_matricula(db: Client, id: str) -> None:
    try:
        # Delete evaluaciones first
        db.table(EVAL_TABLE).delete().eq("matricula_id", id).execute()
        res = db.table(MAT_TABLE).delete().eq("id", id).execute()
        if not res.data:
            raise not_found("Matrícula recuperación", id)
    except Exception as exc:
        if "0 rows" in str(exc) or "not found" in str(exc).lower():
            raise not_found("Matrícula recuperación", id)
        raise supabase_error(exc)


# ── Evaluaciones ───────────────────────────────────────────────

def list_evaluaciones(db: Client, matricula_id: str) -> list[RecEvaluacionOut]:
    try:
        res = (
            db.table(EVAL_TABLE)
            .select("*")
            .eq("matricula_id", matricula_id)
            .order("fecha", desc=True)
            .execute()
        )
        return [RecEvaluacionOut(**r) for r in res.data]
    except Exception as exc:
        raise supabase_error(exc)


def create_evaluacion(db: Client, data: RecEvaluacionCreate) -> RecEvaluacionOut:
    try:
        payload = data.model_dump()
        res = db.table(EVAL_TABLE).insert(payload).execute()
        # Update matricula estado based on average
        _actualizar_estado_matricula(db, data.matricula_id)
        return RecEvaluacionOut(**res.data[0])
    except Exception as exc:
        raise supabase_error(exc)


def delete_evaluacion(db: Client, id: str) -> None:
    try:
        # Get matricula_id before deleting
        eval_res = db.table(EVAL_TABLE).select("matricula_id").eq("id", id).single().execute()
        matricula_id = eval_res.data["matricula_id"] if eval_res.data else None
        res = db.table(EVAL_TABLE).delete().eq("id", id).execute()
        if not res.data:
            raise not_found("Evaluación recuperación", id)
        if matricula_id:
            _actualizar_estado_matricula(db, matricula_id)
    except Exception as exc:
        if "0 rows" in str(exc) or "not found" in str(exc).lower():
            raise not_found("Evaluación recuperación", id)
        raise supabase_error(exc)


def _actualizar_estado_matricula(db: Client, matricula_id: str) -> None:
    """Recalcula el promedio y actualiza el estado de la matrícula."""
    try:
        evals = db.table(EVAL_TABLE).select("nota").eq("matricula_id", matricula_id).execute()
        notas = [e["nota"] for e in evals.data]
        if notas:
            promedio = sum(notas) / len(notas)
            estado = "aprobado" if promedio >= 13 else "en_curso"
        else:
            estado = "pendiente"
        db.table(MAT_TABLE).update({"estado": estado}).eq("id", matricula_id).execute()
    except Exception:
        pass


QUIZ_TABLE = "rec_quiz_preguntas"


def create_quiz(db: Client, data: RecQuizGuardarRequest) -> RecQuizPreguntasOut:
    try:
        payload = {
            "matricula_id": data.matricula_id,
            "titulo": data.titulo,
            "preguntas": data.preguntas,
            "estado": "pendiente",
        }
        res = db.table(QUIZ_TABLE).insert(payload).execute()
        return RecQuizPreguntasOut(**res.data[0])
    except Exception as exc:
        raise supabase_error(exc)


def get_quiz_activo(db: Client, matricula_id: str) -> RecQuizPreguntasOut | None:
    try:
        res = (
            db.table(QUIZ_TABLE)
            .select("*")
            .eq("matricula_id", matricula_id)
            .eq("estado", "pendiente")
            .limit(1)
            .execute()
        )
        if not res.data:
            return None
        return RecQuizPreguntasOut(**res.data[0])
    except Exception as exc:
        raise supabase_error(exc)


def get_quiz(db: Client, quiz_id: str) -> RecQuizPreguntasOut:
    try:
        res = db.table(QUIZ_TABLE).select("*").eq("id", quiz_id).single().execute()
        if not res.data:
            raise not_found("Quiz", quiz_id)
        return RecQuizPreguntasOut(**res.data)
    except Exception as exc:
        if "0 rows" in str(exc) or "not found" in str(exc).lower():
            raise not_found("Quiz", quiz_id)
        raise supabase_error(exc)


def evaluar_quiz(db: Client, quiz_id: str, respuestas: list[int]) -> dict:
    try:
        quiz = get_quiz(db, quiz_id)
        preguntas = quiz.preguntas
        correctas = sum(
            1 for i, r in enumerate(respuestas)
            if i < len(preguntas) and preguntas[i].get("correcta") == r
        )
        total = len(preguntas)
        nota = round((correctas / total) * 20, 2) if total > 0 else 0

        # Marcar quiz como completado
        db.table(QUIZ_TABLE).update({"estado": "completado"}).eq("id", quiz_id).execute()

        # Crear evaluación automática
        eval_data = RecEvaluacionCreate(
            matricula_id=quiz.matricula_id,
            titulo=quiz.titulo,
            nota=nota,
        )
        eval_payload = eval_data.model_dump()
        eval_payload["fecha"] = str(eval_payload["fecha"])
        db.table(EVAL_TABLE).insert(eval_payload).execute()

        _actualizar_estado_matricula(db, quiz.matricula_id)

        return {"nota": nota, "correctas": correctas, "total": total}
    except Exception as exc:
        raise supabase_error(exc)

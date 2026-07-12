from pydantic import BaseModel, Field
from uuid import UUID
from datetime import date, datetime


class RecEstudianteBase(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=200)
    dni: str = Field(..., min_length=8, max_length=15, pattern=r"^\d+$")
    programa: str = Field(..., max_length=200)


class RecEstudianteCreate(RecEstudianteBase):
    pass


class RecEstudianteUpdate(BaseModel):
    nombre: str | None = Field(None, min_length=2, max_length=200)
    dni: str | None = Field(None, min_length=8, max_length=15)
    programa: str | None = Field(None, max_length=200)


class RecEstudianteOut(RecEstudianteBase):
    id: str
    created_at: datetime | None = None


class RecMatriculaBase(BaseModel):
    estudiante_id: str
    curso_nombre: str = Field(..., max_length=300)
    curso_programa: str = Field(..., max_length=200)
    periodo: str = Field(..., max_length=50)
    docente_id: str
    docente_nombre: str = Field(..., max_length=200)


class RecMatriculaCreate(RecMatriculaBase):
    estudiante_nombre: str = Field(..., max_length=200)
    estudiante_dni: str = Field(..., max_length=15)
    estudiante_programa: str = Field(..., max_length=200)
    estado: str = Field("pendiente", pattern=r"^(pendiente|en_curso|aprobado|desaprobado)$")


class RecMatriculaUpdate(BaseModel):
    curso_nombre: str | None = Field(None, max_length=300)
    curso_programa: str | None = Field(None, max_length=200)
    periodo: str | None = Field(None, max_length=50)
    docente_id: str | None = None
    docente_nombre: str | None = Field(None, max_length=200)
    estudiante_nombre: str | None = Field(None, max_length=200)
    estudiante_dni: str | None = Field(None, max_length=15)
    estudiante_programa: str | None = Field(None, max_length=200)
    estado: str | None = Field(None, pattern=r"^(pendiente|en_curso|aprobado|desaprobado)$")


class RecMatriculaOut(RecMatriculaBase):
    id: str
    estudiante_nombre: str
    estudiante_dni: str
    estudiante_programa: str
    estado: str
    created_at: datetime | None = None


class RecEvaluacionBase(BaseModel):
    matricula_id: str
    titulo: str = Field(..., max_length=200)
    nota: float = Field(..., ge=0, le=20)
    fecha: date = Field(default_factory=date.today)


class RecEvaluacionCreate(RecEvaluacionBase):
    pass


class RecEvaluacionOut(RecEvaluacionBase):
    id: str
    created_at: datetime | None = None


class RecQuizGuardarRequest(BaseModel):
    matricula_id: str
    titulo: str = Field(..., max_length=200)
    preguntas: list[dict]


class RecQuizPreguntasOut(BaseModel):
    id: str
    matricula_id: str
    titulo: str
    preguntas: list[dict]
    estado: str
    created_at: datetime | None = None


class RecQuizEvaluarRequest(BaseModel):
    respuestas: list[int]

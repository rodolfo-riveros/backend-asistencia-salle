from __future__ import annotations
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from enum import Enum


# ── Enums ──────────────────────────────────────────────────────────────────────

class TipoInstrumento(str, Enum):
    MANUAL      = "manual"
    COTEJO      = "cotejo"
    RUBRICA     = "rubrica"
    ESCALA      = "escala"
    ANECDOTARIO = "anecdotario"
    GRUPAL      = "grupal"
    QUIZZ       = "quizz"


# ── Indicadores de Logro ───────────────────────────────────────────────────────

class IndicadorCreate(BaseModel):
    unidad_id:       UUID
    periodo_id:      UUID
    codigo:          str  = Field(..., max_length=20)
    descripcion:     str
    peso_porcentaje: int  = Field(..., ge=0, le=100)


class IndicadorUpdate(BaseModel):
    codigo:          str | None = None
    descripcion:     str | None = None
    peso_porcentaje: int | None = Field(None, ge=0, le=100)


class IndicadorOut(BaseModel):
    id:              UUID
    unidad_id:       UUID
    periodo_id:      UUID
    codigo:          str
    descripcion:     str
    peso_porcentaje: int
    created_at:      datetime | None = None

    class Config:
        from_attributes = True


# ── Evaluaciones ───────────────────────────────────────────────────────────────
# POST /config/ recibe un payload que combina indicador + evaluación en un solo paso

class ConfigEvaluacionPayload(BaseModel):
    """
    Payload para POST /evaluaciones/config/
    Cubre Paso 1 (Indicador) + Paso 2/3 (Instrumento) en una sola llamada.
    El backend hace upsert del indicador (por unidad_id+periodo_id+codigo)
    y luego inserta la evaluación vinculada.
    """
    # Datos del indicador
    unidad_id:        UUID
    periodo_id:       UUID
    indicador_codigo: str  = Field(..., max_length=20)
    indicador_desc:   str
    indicador_peso:   int  = Field(..., ge=0, le=100)

    # Datos de la evaluación / instrumento
    nombre:             str
    tipo:               TipoInstrumento = TipoInstrumento.MANUAL
    peso_instrumento:   int = Field(..., ge=0, le=100)
    puntaje_maximo:     int = Field(20, ge=0)
    configuracion_json: dict | None = None   # criterios, niveles, preguntas...


class ConfigEvaluacionOut(BaseModel):
    indicador:  IndicadorOut
    evaluacion: "EvaluacionOut"


class EvaluacionCreate(BaseModel):
    indicador_id:       UUID
    periodo_id:         UUID
    nombre:             str
    tipo:               TipoInstrumento = TipoInstrumento.MANUAL
    peso_instrumento:   int = Field(..., ge=0, le=100)
    puntaje_maximo:     int = Field(20, ge=0)
    configuracion_json: dict | None = None


class EvaluacionUpdate(BaseModel):
    nombre:             str | None = None
    tipo:               TipoInstrumento | None = None
    peso_instrumento:   int | None = Field(None, ge=0, le=100)
    puntaje_maximo:     int | None = Field(None, ge=0)
    configuracion_json: dict | None = None


class EvaluacionOut(BaseModel):
    id:                 UUID
    indicador_id:       UUID | None
    periodo_id:         UUID | None
    nombre:             str
    tipo:               str
    peso_instrumento:   int
    puntaje_maximo:     int
    configuracion_json: dict | None = None
    created_at:         datetime | None = None
    # Campos extra del JOIN con indicadores_logro (presente en GET /config/)
    indicador_codigo:  str | None = None
    indicador_desc:    str | None = None
    indicador_peso:    int | None = None

    class Config:
        from_attributes = True


# ── Grupos ─────────────────────────────────────────────────────────────────────

class IntegranteIn(BaseModel):
    alumno_id: UUID


class GrupoIn(BaseModel):
    nombre_grupo: str
    integrantes:  list[UUID] = Field(default_factory=list)


class GruposPayload(BaseModel):
    """POST /evaluaciones/grupos/ — Paso 4: conformación de equipos."""
    evaluacion_id: UUID
    grupos:        list[GrupoIn]


class GrupoCreate(BaseModel):
    evaluacion_id: UUID
    nombre_grupo:  str


class GrupoOut(BaseModel):
    id:            UUID
    evaluacion_id: UUID | None
    nombre_grupo:  str
    created_at:    datetime | None = None
    integrantes:   list[UUID] = []

    class Config:
        from_attributes = True


# ── Calificaciones ─────────────────────────────────────────────────────────────

class CalificacionCreate(BaseModel):
    """POST /evaluaciones/calificar/ — nota individual."""
    evaluacion_id: UUID
    alumno_id:     UUID
    puntaje:       float = Field(..., ge=0)
    observacion:   str | None = None
    detalles_json: dict | None = None   # evidencia (celdas rúbrica, ítems cotejo...)


class CalificacionUpdate(BaseModel):
    puntaje:       float | None = Field(None, ge=0)
    observacion:   str | None = None
    detalles_json: dict | None = None


class CalificacionOut(BaseModel):
    id:            UUID
    evaluacion_id: UUID | None
    alumno_id:     UUID | None
    puntaje:       float
    observacion:   str | None = None
    detalles_json: dict | None = None
    updated_at:    datetime | None = None

    class Config:
        from_attributes = True


class NotasGamificacionPayload(BaseModel):
    """POST /evaluaciones/notas-gamificacion/ — bulk insert al terminar el Quizz."""
    evaluacion_id: UUID
    notas: list[dict]   # [{alumno_id, aciertos, total_preguntas}]


# ── Registro auxiliar completo (GET /config/{unidad_id}/{periodo_id}) ──────────

class PromedioAlumno(BaseModel):
    alumno_id:     UUID
    alumno_nombre: str
    promedio:      float
    detalle:       list[dict] = []


class RegistroAuxiliarOut(BaseModel):
    unidad_id:      UUID
    periodo_id:     UUID
    indicadores:    list[IndicadorOut]
    evaluaciones:   list[EvaluacionOut]
    grupos:         list[GrupoOut]
    calificaciones: list[CalificacionOut]
    promedios:      list[PromedioAlumno] = []


# ── Save-all (upsert masivo legacy) ───────────────────────────────────────────

class SaveAllPayload(BaseModel):
    unidad_id:      UUID
    periodo_id:     UUID
    indicadores:    list[dict] = Field(default_factory=list)
    evaluaciones:   list[dict] = Field(default_factory=list)
    calificaciones: list[dict] = Field(default_factory=list)

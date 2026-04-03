from pydantic import BaseModel, Field
from uuid import UUID
from datetime import date
from enum import Enum


# ── Asignación Docente ────────────────────────────────────────

class AsignacionBase(BaseModel):
    docente_id: UUID
    unidad_id:  UUID
    periodo_id: UUID 


class AsignacionCreate(AsignacionBase):
    pass


class AsignacionUpdate(BaseModel):
    docente_id: UUID | None = None
    unidad_id: UUID | None = None
    periodo_id: UUID | None = None


class AsignacionOut(BaseModel):
    id:         UUID
    docente_id: UUID
    unidad_id:  UUID
    periodo_id: UUID

    class Config:
        from_attributes = True


class AsignacionDetalle(AsignacionOut):
    """Con nombres para mostrar en la UI."""
    docente_nombre: str | None = None
    unidad_nombre:  str | None = None
    programa_nombre: str | None = None
    semestre: str | None = None
    periodo_nombre: str | None = None


# ── Asistencias ───────────────────────────────────────────────

class EstadoAsistencia(str, Enum):
    PRESENTE     = "P"
    FALTA        = "F"
    JUSTIFICADO  = "J"
    TARDE        = "T"


class AsistenciaBase(BaseModel):
    alumno_id:   UUID
    unidad_id:   UUID
    periodo_id:  UUID  # ← AGREGADO
    fecha:       date = Field(default_factory=date.today)
    estado:      EstadoAsistencia
    observacion: str | None = Field(None, max_length=500)


class AsistenciaCreate(AsistenciaBase):
    pass


class AsistenciaUpsert(BaseModel):
    """Para registrar varios alumnos en una sola llamada (pase de lista)."""
    unidad_id:   UUID
    periodo_id:  UUID  # ← AGREGADO - CAMPO CRÍTICO
    fecha:       date = Field(default_factory=date.today)
    registros: list[dict] = Field(
        ...,
        description="Lista de {alumno_id, estado, observacion?}",
    )


class AsistenciaUpdate(BaseModel):
    estado:      EstadoAsistencia | None = None
    observacion: str | None = None


class AsistenciaOut(AsistenciaBase):
    id:         UUID
    docente_id: UUID

    class Config:
        from_attributes = True


# ── Reportes ──────────────────────────────────────────────────

class AsistenciaDetalle(BaseModel):
    id:              UUID
    fecha:           date
    estado:          str
    observacion:     str | None
    alumno:          str
    dni:             str
    unidad:          str
    semestre:        str
    programa:        str
    docente:         str


class ResumenAsistencia(BaseModel):
    alumno_id:    UUID
    alumno:       str
    dni:          str
    total:        int
    presentes:    int
    tardanzas:    int
    justificados: int
    faltas:       int
    porcentaje_asistencia: float
from pydantic import BaseModel, Field
from uuid import UUID
from enum import Enum


class SemestreEnum(str, Enum):
    I   = "I"
    II  = "II"
    III = "III"
    IV  = "IV"
    V   = "V"
    VI  = "VI"


class UnidadBase(BaseModel):
    nombre:      str          = Field(..., min_length=2, max_length=200)
    programa_id: UUID
    semestre:    SemestreEnum


class UnidadCreate(UnidadBase):
    pass


class UnidadUpdate(BaseModel):
    nombre:   str | None          = Field(None, min_length=2, max_length=200)
    semestre: SemestreEnum | None = None


class UnidadOut(UnidadBase):
    id: UUID

    class Config:
        from_attributes = True


class UnidadConPrograma(UnidadOut):
    """Incluye nombre del programa (viene de JOIN o vista)."""
    programa_nombre: str | None = None

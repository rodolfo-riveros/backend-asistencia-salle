from pydantic import BaseModel, Field
from uuid import UUID
from app.schemas.unidades import SemestreEnum


class AlumnoBase(BaseModel):
    nombre:      str          = Field(..., min_length=2, max_length=200)
    programa_id: UUID
    semestre:    SemestreEnum
    dni:         str          = Field(..., min_length=8, max_length=15, pattern=r"^\d+$")


class AlumnoCreate(AlumnoBase):
    seccion: str = Field("U", min_length=1, max_length=10)


class AlumnoUpdate(BaseModel):
    nombre:      str | None          = Field(None, min_length=2, max_length=200)
    programa_id: UUID | None         = None
    semestre:    SemestreEnum | None = None
    dni:         str | None          = Field(None, min_length=8, max_length=15)


class AlumnoOut(AlumnoBase):
    id: UUID

    class Config:
        from_attributes = True


class AlumnoConPrograma(AlumnoOut):
    programa_nombre: str | None = None
    seccion:         str | None = Field("U", min_length=1, max_length=10)

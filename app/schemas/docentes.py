from pydantic import BaseModel, Field
from uuid import UUID


class DocenteBase(BaseModel):
    nombre:        str  = Field(..., min_length=2, max_length=200)
    especialidad:  str | None = Field(None, max_length=200)
    es_transversal: bool = False


class DocenteCreate(DocenteBase):
    """El admin crea el docente; 'id' viene del UUID de auth.users."""
    id: UUID


class DocenteUpdate(BaseModel):
    nombre:         str | None = Field(None, min_length=2, max_length=200)
    especialidad:   str | None = None
    es_transversal: bool | None = None


class DocenteOut(DocenteBase):
    id: UUID

    class Config:
        from_attributes = True

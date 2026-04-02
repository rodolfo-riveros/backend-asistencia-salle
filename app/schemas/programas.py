from pydantic import BaseModel, Field
from uuid import UUID


class ProgramaBase(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=200)
    codigo: str = Field(..., min_length=2, max_length=20, pattern=r"^[A-Z0-9_]+$")


class ProgramaCreate(ProgramaBase):
    pass


class ProgramaUpdate(BaseModel):
    nombre: str | None = Field(None, min_length=2, max_length=200)
    codigo: str | None = Field(None, min_length=2, max_length=20)


class ProgramaOut(ProgramaBase):
    id: UUID

    class Config:
        from_attributes = True

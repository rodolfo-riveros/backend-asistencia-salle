from supabase import Client
from app.schemas import ProgramaCreate, ProgramaUpdate, ProgramaOut
from app.exceptions import not_found, supabase_error

TABLE = "programas_estudio"


def list_programas(db: Client) -> list[ProgramaOut]:
    try:
        res = db.table(TABLE).select("*").order("nombre").execute()
        return [ProgramaOut(**r) for r in res.data]
    except Exception as exc:
        raise supabase_error(exc)


def get_programa(db: Client, id: str) -> ProgramaOut:
    try:
        res = db.table(TABLE).select("*").eq("id", id).single().execute()
        if not res.data:
            raise not_found("Programa", id)
        return ProgramaOut(**res.data)
    except Exception as exc:
        if "not found" in str(exc).lower() or "0 rows" in str(exc):
            raise not_found("Programa", id)
        raise supabase_error(exc)


def create_programa(db: Client, data: ProgramaCreate) -> ProgramaOut:
    try:
        res = db.table(TABLE).insert(data.model_dump()).execute()
        return ProgramaOut(**res.data[0])
    except Exception as exc:
        raise supabase_error(exc)


def update_programa(db: Client, id: str, data: ProgramaUpdate) -> ProgramaOut:
    payload = data.model_dump(exclude_none=True)
    if not payload:
        return get_programa(db, id)
    try:
        res = db.table(TABLE).update(payload).eq("id", id).execute()
        if not res.data:
            raise not_found("Programa", id)
        return ProgramaOut(**res.data[0])
    except Exception as exc:
        raise supabase_error(exc)


def delete_programa(db: Client, id: str) -> None:
    try:
        res = db.table(TABLE).delete().eq("id", id).execute()
        if not res.data:
            raise not_found("Programa", id)
    except Exception as exc:
        raise supabase_error(exc)

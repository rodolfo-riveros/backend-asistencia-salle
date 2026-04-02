from supabase import Client
from app.schemas import DocenteCreate, DocenteUpdate, DocenteOut
from app.exceptions import not_found, supabase_error

TABLE = "docentes"


def list_docentes(
    db: Client,
    es_transversal: bool | None = None,
) -> list[DocenteOut]:
    try:
        q = db.table(TABLE).select("*").order("nombre")
        if es_transversal is not None:
            q = q.eq("es_transversal", es_transversal)
        res = q.execute()
        return [DocenteOut(**r) for r in res.data]
    except Exception as exc:
        raise supabase_error(exc)


def get_docente(db: Client, id: str) -> DocenteOut:
    try:
        res = db.table(TABLE).select("*").eq("id", id).single().execute()
        if not res.data:
            raise not_found("Docente", id)
        return DocenteOut(**res.data)
    except Exception as exc:
        if "0 rows" in str(exc) or "not found" in str(exc).lower():
            raise not_found("Docente", id)
        raise supabase_error(exc)


def create_docente(db: Client, data: DocenteCreate) -> DocenteOut:
    """
    El admin registra el perfil del docente. El UUID debe coincidir
    con el usuario ya creado en Supabase Auth.
    """
    try:
        payload = data.model_dump()
        payload["id"] = str(payload["id"])
        res = db.table(TABLE).insert(payload).execute()
        return DocenteOut(**res.data[0])
    except Exception as exc:
        raise supabase_error(exc)


def update_docente(db: Client, id: str, data: DocenteUpdate) -> DocenteOut:
    payload = data.model_dump(exclude_none=True)
    if not payload:
        return get_docente(db, id)
    try:
        res = db.table(TABLE).update(payload).eq("id", id).execute()
        if not res.data:
            raise not_found("Docente", id)
        return DocenteOut(**res.data[0])
    except Exception as exc:
        raise supabase_error(exc)


def delete_docente(db: Client, id: str) -> None:
    try:
        res = db.table(TABLE).delete().eq("id", id).execute()
        if not res.data:
            raise not_found("Docente", id)
    except Exception as exc:
        raise supabase_error(exc)

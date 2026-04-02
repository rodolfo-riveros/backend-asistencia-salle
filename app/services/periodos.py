from supabase import Client
from app.schemas import PeriodoCreate, PeriodoUpdate, PeriodoOut
from app.exceptions import not_found, supabase_error

TABLE = "periodos_academicos"

def list_periodos(db: Client) -> list[PeriodoOut]:
    try:
        # Listamos todos los periodos ordenados por nombre (ej: 2024-I, 2024-II)
        res = db.table(TABLE).select("*").order("nombre", desc=True).execute()
        return [PeriodoOut(**r) for r in res.data]
    except Exception as exc:
        raise supabase_error(exc)

def get_periodo(db: Client, id: str) -> PeriodoOut:
    try:
        res = db.table(TABLE).select("*").eq("id", id).single().execute()
        if not res.data:
            raise not_found("Periodo académico", id)
        return PeriodoOut(**res.data)
    except Exception as exc:
        if "0 rows" in str(exc) or "not found" in str(exc).lower():
            raise not_found("Periodo académico", id)
        raise supabase_error(exc)

def create_periodo(db: Client, data: PeriodoCreate) -> PeriodoOut:
    try:
        payload = data.model_dump()
        # Si el nuevo periodo es activo, desactivamos el resto primero
        if payload.get("es_activo"):
            db.table(TABLE).update({"es_activo": False}).neq("id", "00000000-0000-0000-0000-000000000000").execute()
            
        res = db.table(TABLE).insert(payload).execute()
        return PeriodoOut(**res.data[0])
    except Exception as exc:
        raise supabase_error(exc)

def update_periodo(db: Client, id: str, data: PeriodoUpdate) -> PeriodoOut:
    payload = data.model_dump(exclude_none=True)
    if not payload:
        return get_periodo(db, id)
    try:
        # Lógica de exclusividad: Solo un periodo puede estar activo a la vez
        if payload.get("es_activo") is True:
            # Desactivamos todos los periodos que NO sean este
            db.table(TABLE).update({"es_activo": False}).neq("id", id).execute()

        res = db.table(TABLE).update(payload).eq("id", id).execute()
        if not res.data:
            raise not_found("Periodo académico", id)
        return PeriodoOut(**res.data[0])
    except Exception as exc:
        raise supabase_error(exc)

def delete_periodo(db: Client, id: str) -> None:
    try:
        res = db.table(TABLE).delete().eq("id", id).execute()
        if not res.data:
            raise not_found("Periodo académico", id)
    except Exception as exc:
        raise supabase_error(exc)
from supabase import Client
from app.schemas import UnidadCreate, UnidadUpdate, UnidadOut, UnidadConPrograma
from app.exceptions import not_found, supabase_error

TABLE = "unidades_didacticas"


def list_unidades(
    db: Client,
    programa_id: str | None = None,
    semestre: str | None = None,
) -> list[UnidadConPrograma]:
    try:
        q = db.table(TABLE).select(
            "*, programas_estudio(nombre)"
        ).order("semestre").order("nombre")
        if programa_id:
            q = q.eq("programa_id", programa_id)
        if semestre:
            q = q.eq("semestre", semestre)
        res = q.execute()
        return [
            UnidadConPrograma(
                **{k: v for k, v in r.items() if k != "programas_estudio"},
                programa_nombre=r.get("programas_estudio", {}).get("nombre"),
            )
            for r in res.data
        ]
    except Exception as exc:
        raise supabase_error(exc)


def get_unidad(db: Client, id: str) -> UnidadConPrograma:
    try:
        res = (
            db.table(TABLE)
            .select("*, programas_estudio(nombre)")
            .eq("id", id)
            .single()
            .execute()
        )
        if not res.data:
            raise not_found("Unidad didáctica", id)
        r = res.data
        return UnidadConPrograma(
            **{k: v for k, v in r.items() if k != "programas_estudio"},
            programa_nombre=r.get("programas_estudio", {}).get("nombre"),
        )
    except Exception as exc:
        if "0 rows" in str(exc) or "not found" in str(exc).lower():
            raise not_found("Unidad didáctica", id)
        raise supabase_error(exc)


def create_unidad(db: Client, data: UnidadCreate) -> UnidadOut:
    try:
        payload = data.model_dump()
        payload["programa_id"] = str(payload["programa_id"])
        res = db.table(TABLE).insert(payload).execute()
        return UnidadOut(**res.data[0])
    except Exception as exc:
        raise supabase_error(exc)


def update_unidad(db: Client, id: str, data: UnidadUpdate) -> UnidadOut:
    payload = data.model_dump(exclude_none=True)
    if not payload:
        return get_unidad(db, id)
    try:
        res = db.table(TABLE).update(payload).eq("id", id).execute()
        if not res.data:
            raise not_found("Unidad didáctica", id)
        return UnidadOut(**res.data[0])
    except Exception as exc:
        raise supabase_error(exc)


def delete_unidad(db: Client, id: str) -> None:
    try:
        res = db.table(TABLE).delete().eq("id", id).execute()
        if not res.data:
            raise not_found("Unidad didáctica", id)
    except Exception as exc:
        raise supabase_error(exc)

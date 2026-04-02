from supabase import Client
from app.schemas import AlumnoCreate, AlumnoUpdate, AlumnoOut, AlumnoConPrograma
from app.exceptions import not_found, supabase_error

TABLE = "alumnos"


def list_alumnos(
    db: Client,
    programa_id: str | None = None,
    semestre: str | None = None,
    search: str | None = None,
) -> list[AlumnoConPrograma]:
    try:
        q = db.table(TABLE).select(
            "*, programas_estudio(nombre)"
        ).order("nombre")
        if programa_id:
            q = q.eq("programa_id", programa_id)
        if semestre:
            q = q.eq("semestre", semestre)
        if search:
            q = q.ilike("nombre", f"%{search}%")
        res = q.execute()
        return [
            AlumnoConPrograma(
                **{k: v for k, v in r.items() if k != "programas_estudio"},
                programa_nombre=r.get("programas_estudio", {}).get("nombre"),
            )
            for r in res.data
        ]
    except Exception as exc:
        raise supabase_error(exc)


def get_alumno(db: Client, id: str) -> AlumnoConPrograma:
    try:
        res = (
            db.table(TABLE)
            .select("*, programas_estudio(nombre)")
            .eq("id", id)
            .single()
            .execute()
        )
        if not res.data:
            raise not_found("Alumno", id)
        r = res.data
        return AlumnoConPrograma(
            **{k: v for k, v in r.items() if k != "programas_estudio"},
            programa_nombre=r.get("programas_estudio", {}).get("nombre"),
        )
    except Exception as exc:
        if "0 rows" in str(exc) or "not found" in str(exc).lower():
            raise not_found("Alumno", id)
        raise supabase_error(exc)


def get_alumno_by_dni(db: Client, dni: str) -> AlumnoConPrograma:
    try:
        res = (
            db.table(TABLE)
            .select("*, programas_estudio(nombre)")
            .eq("dni", dni)
            .single()
            .execute()
        )
        if not res.data:
            raise not_found("Alumno", f"DNI {dni}")
        r = res.data
        return AlumnoConPrograma(
            **{k: v for k, v in r.items() if k != "programas_estudio"},
            programa_nombre=r.get("programas_estudio", {}).get("nombre"),
        )
    except Exception as exc:
        if "0 rows" in str(exc) or "not found" in str(exc).lower():
            raise not_found("Alumno", f"DNI {dni}")
        raise supabase_error(exc)


def create_alumno(db: Client, data: AlumnoCreate) -> AlumnoOut:
    try:
        payload = data.model_dump()
        payload["programa_id"] = str(payload["programa_id"])
        res = db.table(TABLE).insert(payload).execute()
        return AlumnoOut(**res.data[0])
    except Exception as exc:
        raise supabase_error(exc)


def update_alumno(db: Client, id: str, data: AlumnoUpdate) -> AlumnoOut:
    payload = data.model_dump(exclude_none=True)
    if "programa_id" in payload:
        payload["programa_id"] = str(payload["programa_id"])
    if not payload:
        return get_alumno(db, id)
    try:
        res = db.table(TABLE).update(payload).eq("id", id).execute()
        if not res.data:
            raise not_found("Alumno", id)
        return AlumnoOut(**res.data[0])
    except Exception as exc:
        raise supabase_error(exc)


def delete_alumno(db: Client, id: str) -> None:
    try:
        res = db.table(TABLE).delete().eq("id", id).execute()
        if not res.data:
            raise not_found("Alumno", id)
    except Exception as exc:
        raise supabase_error(exc)


def list_alumnos_por_unidad(db: Client, unidad_id: str) -> list[AlumnoConPrograma]:
    """
    Devuelve los alumnos que pertenecen al programa+semestre de la unidad.
    Usa la vista v_alumnos_por_unidad creada en el SQL.
    """
    try:
        res = (
            db.table("v_alumnos_por_unidad")
            .select("alumno_id, alumno_nombre, dni, semestre, programa_id, programa_nombre")
            .eq("unidad_id", unidad_id)
            .order("alumno_nombre")
            .execute()
        )
        return [
            AlumnoConPrograma(
                id=r["alumno_id"],
                nombre=r["alumno_nombre"],
                dni=r["dni"],
                semestre=r["semestre"],
                programa_id=r["programa_id"],
                programa_nombre=r["programa_nombre"],
            )
            for r in res.data
        ]
    except Exception as exc:
        raise supabase_error(exc)

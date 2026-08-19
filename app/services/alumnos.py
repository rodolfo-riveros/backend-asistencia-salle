from supabase import Client
from fastapi import HTTPException
from app.schemas import (
    AlumnoCreate, AlumnoUpdate, AlumnoOut, AlumnoConPrograma, PromoverSalonRequest,
)
from app.exceptions import not_found, supabase_error, bad_request

TABLE = "alumnos"


def _periodo_activo(db: Client) -> str | None:
    res = db.table("periodos_academicos").select("id").eq("es_activo", True).limit(1).execute()
    return res.data[0]["id"] if res.data else None


def _sincronizar_matricula(
    db: Client,
    alumno_id: str,
    programa_id: str,
    semestre: str,
) -> None:
    """Asegura que el alumno tenga una matrícula en el período activo con el semestre indicado."""
    periodo_activo = _periodo_activo(db)
    if not periodo_activo:
        return

    existing = (
        db.table("matriculas")
        .select("id")
        .eq("alumno_id", alumno_id)
        .eq("periodo_id", periodo_activo)
        .limit(1)
        .execute()
    )

    payload = {
        "periodo_id": periodo_activo,
        "programa_id": str(programa_id),
        "semestre": semestre,
    }
    if existing.data:
        db.table("matriculas").update(payload).eq("id", existing.data[0]["id"]).execute()
    else:
        db.table("matriculas").insert({"alumno_id": alumno_id, **payload}).execute()


def _fetch_alumno_con_programa(db: Client, q) -> list[AlumnoConPrograma]:
    res = q.execute()
    results = []
    for r in res.data:
        row = {k: v for k, v in r.items() if k not in ("programas_estudio", "seccion")}
        results.append(AlumnoConPrograma(
            **row,
            programa_nombre=r.get("programas_estudio", {}).get("nombre"),
        ))
    return results


def list_alumnos(
    db: Client,
    programa_id: str | None = None,
    semestre: str | None = None,
    search: str | None = None,
) -> list[AlumnoConPrograma]:
    try:
        q = db.table("v_alumnos_listado").select(
            "*, programas_estudio(nombre)"
        ).order("nombre")
        if programa_id:
            q = q.eq("programa_id", programa_id)
        if semestre:
            q = q.eq("semestre", semestre)
        if search:
            q = q.ilike("nombre", f"%{search}%")
        return _fetch_alumno_con_programa(db, q)
    except Exception as exc:
        raise supabase_error(exc)


def get_alumno(db: Client, id: str) -> AlumnoConPrograma:
    try:
        q = db.table("v_alumnos_listado").select(
            "*, programas_estudio(nombre)"
        ).eq("id", id).single()
        res = q.execute()
        if not res.data:
            raise not_found("Alumno", id)
        rows = _fetch_alumno_con_programa(db, db.table("v_alumnos_listado").select("*, programas_estudio(nombre)").eq("id", id))
        return rows[0]
    except Exception as exc:
        if "0 rows" in str(exc) or "not found" in str(exc).lower():
            raise not_found("Alumno", id)
        raise supabase_error(exc)


def get_alumno_by_dni(db: Client, dni: str) -> AlumnoConPrograma:
    try:
        q = db.table("v_alumnos_listado").select(
            "*, programas_estudio(nombre)"
        ).eq("dni", dni).single()
        res = q.execute()
        if not res.data:
            raise not_found("Alumno", f"DNI {dni}")
        rows = _fetch_alumno_con_programa(db, db.table("v_alumnos_listado").select("*, programas_estudio(nombre)").eq("dni", dni))
        return rows[0]
    except Exception as exc:
        if "0 rows" in str(exc) or "not found" in str(exc).lower():
            raise not_found("Alumno", f"DNI {dni}")
        raise supabase_error(exc)


def create_alumno(db: Client, data: AlumnoCreate) -> AlumnoOut:
    try:
        # 1a. Verificar si ya existe por DNI
        existing = db.table(TABLE).select("id").eq("dni", data.dni).limit(1).execute()
        if existing.data:
            alumno_id = existing.data[0]["id"]
        else:
            # 1b. Crear alumno en el padron maestro
            payload = data.model_dump()
            payload["programa_id"] = str(payload["programa_id"])
            res = db.table(TABLE).insert(payload).execute()
            alumno_id = res.data[0]["id"]

        # 2. Crear matricula
        periodo_id = _periodo_activo(db)
        matricula_payload = {
            "alumno_id": alumno_id,
            "periodo_id": periodo_id,
            "programa_id": str(data.programa_id),
            "semestre": data.semestre.value,
        }
        db.table("matriculas").insert(matricula_payload).execute()

        # Retornar el alumno creado/existente
        out = db.table(TABLE).select("*").eq("id", alumno_id).single().execute()
        return AlumnoOut(**out.data)
    except Exception as exc:
        raise supabase_error(exc)


def update_alumno(db: Client, id: str, data: AlumnoUpdate) -> AlumnoOut:
    payload = data.model_dump(exclude_none=True)
    if "programa_id" in payload:
        payload["programa_id"] = str(payload["programa_id"])
    if "semestre" in payload:
        payload["semestre"] = payload["semestre"].value
    if not payload:
        return get_alumno(db, id)
    try:
        res = db.table(TABLE).update(payload).eq("id", id).execute()
        if not res.data:
            raise not_found("Alumno", id)
        # Mantener la matrícula del período activo sincronizada con el nuevo semestre
        if "semestre" in payload:
            programa_id = payload.get("programa_id") or res.data[0].get("programa_id")
            _sincronizar_matricula(db, id, programa_id, payload["semestre"])
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


def list_alumnos_por_unidad(
    db: Client,
    unidad_id: str,
) -> list[AlumnoConPrograma]:
    try:
        q = (
            db.table("v_alumnos_por_unidad")
            .select("alumno_id, alumno_nombre, dni, semestre, programa_id, programa_nombre")
            .eq("unidad_id", unidad_id)
        )
        res = q.order("alumno_nombre").execute()
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


def promover_salon(
    db: Client,
    data: PromoverSalonRequest,
) -> dict:
    """Promueve masivamente todo un salón (programa + semestre) al siguiente semestre."""
    try:
        if data.semestre_actual == data.semestre_nuevo:
            raise bad_request("El semestre actual y el nuevo no pueden ser iguales")

        # 1. Contar alumnos que serán promovidos
        res = (
            db.table(TABLE)
            .select("id")
            .eq("programa_id", str(data.programa_id))
            .eq("semestre", data.semestre_actual.value)
            .execute()
        )
        if not res.data:
            raise bad_request(
                f"No hay alumnos en semestre {data.semestre_actual.value} para el programa seleccionado"
            )

        alumno_ids = [r["id"] for r in res.data]

        # 2. Actualizar semestre en el padrón maestro
        db.table(TABLE).update(
            {"semestre": data.semestre_nuevo.value}
        ).in_("id", alumno_ids).execute()

        # 3. Asegurar matrícula en el período activo con el semestre nuevo
        periodo_activo = _periodo_activo(db)
        if periodo_activo:
            existing = (
                db.table("matriculas")
                .select("alumno_id")
                .eq("periodo_id", periodo_activo)
                .in_("alumno_id", alumno_ids)
                .execute()
            )
            existentes = {r["alumno_id"] for r in existing.data}

            # Actualizar matrículas del período activo ya existentes
            if existentes:
                db.table("matriculas").update(
                    {"semestre": data.semestre_nuevo.value}
                ).eq("periodo_id", periodo_activo).in_("alumno_id", list(existentes)).execute()

            # Crear matrícula nueva para quienes no la tienen en el período activo
            nuevos = [aid for aid in alumno_ids if aid not in existentes]
            if nuevos:
                db.table("matriculas").insert([
                    {
                        "alumno_id": aid,
                        "periodo_id": periodo_activo,
                        "programa_id": str(data.programa_id),
                        "semestre": data.semestre_nuevo.value,
                    }
                    for aid in nuevos
                ]).execute()

        return {"promovidos": len(alumno_ids)}
    except HTTPException:
        raise
    except Exception as exc:
        raise supabase_error(exc)


def reparar_matriculas(
    db: Client,
    programa_id: str | None = None,
) -> dict:
    """Asegura que cada alumno del padrón tenga matrícula en el período activo con su semestre actual."""
    try:
        periodo_activo = _periodo_activo(db)
        if not periodo_activo:
            raise bad_request("No hay un período académico activo")

        q = db.table(TABLE).select("id, programa_id, semestre")
        if programa_id:
            q = q.eq("programa_id", str(programa_id))
        res = q.execute()
        if not res.data:
            raise bad_request("No hay alumnos en el padrón")

        alumno_ids = [r["id"] for r in res.data]

        existing = (
            db.table("matriculas")
            .select("alumno_id")
            .eq("periodo_id", periodo_activo)
            .in_("alumno_id", alumno_ids)
            .execute()
        )
        existentes = {r["alumno_id"] for r in existing.data}

        # Agrupar por (programa_id, semestre) para operar en lote
        por_grupo: dict[tuple[str, str], list[str]] = {}
        for r in res.data:
            por_grupo.setdefault((str(r["programa_id"]), str(r["semestre"])), []).append(r["id"])

        creados = 0
        actualizados = 0
        for (pid, sem), ids in por_grupo.items():
            payload = {"periodo_id": periodo_activo, "programa_id": pid, "semestre": sem}
            actualizables = [i for i in ids if i in existentes]
            if actualizables:
                db.table("matriculas").update(
                    payload
                ).eq("periodo_id", periodo_activo).in_("alumno_id", actualizables).execute()
                actualizados += len(actualizables)
            nuevos = [i for i in ids if i not in existentes]
            if nuevos:
                db.table("matriculas").insert(
                    [{"alumno_id": i, **payload} for i in nuevos]
                ).execute()
                creados += len(nuevos)

        return {"creados": creados, "actualizados": actualizados}
    except HTTPException:
        raise
    except Exception as exc:
        raise supabase_error(exc)

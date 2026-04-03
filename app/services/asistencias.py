from __future__ import annotations
from datetime import date
from supabase import Client
from app.schemas import (
    AsignacionCreate, AsignacionUpdate, AsignacionOut, AsignacionDetalle,
    AsistenciaCreate, AsistenciaUpdate, AsistenciaOut, AsistenciaUpsert,
    AsistenciaDetalle, ResumenAsistencia, EstadoAsistencia,
)
from app.exceptions import not_found, supabase_error, bad_request

ASIG_TABLE  = "asignacion_docente"
ASIST_TABLE = "asistencias"


# ══════════════════════════════════════════════════════════════
# ASIGNACIÓN DOCENTE
# ══════════════════════════════════════════════════════════════

def list_asignaciones(
    db: Client,
    docente_id: str | None = None,
    periodo: str | None = None,
) -> list[AsignacionDetalle]:
    try:
        # Nota: Usamos 'periodo_academico' (singular) que es la columna real en SQL
        q = db.table(ASIG_TABLE).select(
            "*, docentes(nombre), unidades_didacticas(nombre, semestre, programas_estudio(nombre))"
        ).order("periodo_academico", desc=True)
        
        if docente_id:
            q = q.eq("docente_id", docente_id)
        if periodo:
            q = q.eq("periodo_academico", periodo)
            
        res = q.execute()
        return [_map_asignacion(r) for r in res.data]
    except Exception as exc:
        raise supabase_error(exc)


def get_asignacion(db: Client, id: str) -> AsignacionDetalle:
    try:
        res = (
            db.table(ASIG_TABLE)
            .select("*, docentes(nombre), unidades_didacticas(nombre, semestre, programas_estudio(nombre))")
            .eq("id", id)
            .single()
            .execute()
        )
        if not res.data:
            raise not_found("Asignación", id)
        return _map_asignacion(res.data)
    except Exception as exc:
        if "0 rows" in str(exc) or "not found" in str(exc).lower():
            raise not_found("Asignación", id)
        raise supabase_error(exc)


def create_asignacion(db: Client, data: AsignacionCreate) -> AsignacionOut:
    try:
        # MAPEO CRÍTICO: 
        # Llave (BD): "periodo_academico" (singular)
        # Valor (Pydantic): data.periodo_academicos (plural)
        payload = {
            "docente_id":        str(data.docente_id),
            "unidad_id":         str(data.unidad_id),
            "periodo_academico": data.periodo_academicos, 
        }
        res = db.table(ASIG_TABLE).insert(payload).execute()
        
        # Al retornar, renombramos para que Pydantic no falle al validar AsignacionOut
        row = res.data[0]
        if "periodo_academico" in row:
            row["periodo_academicos"] = row.pop("periodo_academico")
            
        return AsignacionOut(**row)
    except Exception as exc:
        raise supabase_error(exc)


def delete_asignacion(db: Client, id: str) -> None:
    try:
        res = db.table(ASIG_TABLE).delete().eq("id", id).execute()
        if not res.data:
            raise not_found("Asignación", id)
    except Exception as exc:
        raise supabase_error(exc)


def _map_asignacion(r: dict) -> AsignacionDetalle:
    ud = r.get("unidades_didacticas") or {}
    pe = ud.get("programas_estudio") or {}
    
    # Renombramos el campo de la BD al nombre del esquema Pydantic
    periodo_val = r.get("periodo_academicos") or r.get("periodo_academico")
    
    return AsignacionDetalle(
        **{k: v for k, v in r.items()
           if k not in ("docentes", "unidades_didacticas", "periodo_academico", "periodo_academicos")},
        periodo_academicos = periodo_val,
        docente_nombre  = (r.get("docentes") or {}).get("nombre"),
        unidad_nombre   = ud.get("nombre"),
        semestre        = ud.get("semestre"),
        programa_nombre = pe.get("nombre"),
    )


# ══════════════════════════════════════════════════════════════
# ASISTENCIAS
# ══════════════════════════════════════════════════════════════

def registrar_asistencia_bulk(
    db: Client,
    data: AsistenciaUpsert,
    docente_id: str,
) -> list[AsistenciaOut]:
    """
    Registra o actualiza el pase de lista completo de una unidad en una fecha.
    Usa upsert para evitar duplicados (unique: alumno_id + unidad_id + fecha).
    """
    if not data.registros:
        raise bad_request("La lista de registros no puede estar vacía")

    rows = []
    for item in data.registros:
        alumno_id = str(item.get("alumno_id", ""))
        estado    = item.get("estado")
        if not alumno_id or not estado:
            raise bad_request(f"Registro inválido: {item}. Requiere alumno_id y estado.")
        if estado not in [e.value for e in EstadoAsistencia]:
            raise bad_request(f"Estado '{estado}' no válido. Use: P, F, J, T")
        rows.append({
            "alumno_id":   alumno_id,
            "unidad_id":   str(data.unidad_id),
            "docente_id":  docente_id,
            "fecha":       data.fecha.isoformat(),
            "estado":      estado,
            "observacion": item.get("observacion"),
        })
    try:
        res = (
            db.table(ASIST_TABLE)
            .upsert(rows, on_conflict="alumno_id,unidad_id,fecha")
            .execute()
        )
        return [AsistenciaOut(**r) for r in res.data]
    except Exception as exc:
        raise supabase_error(exc)


def get_asistencia(db: Client, id: str) -> AsistenciaOut:
    try:
        res = db.table(ASIST_TABLE).select("*").eq("id", id).single().execute()
        if not res.data:
            raise not_found("Asistencia", id)
        return AsistenciaOut(**res.data)
    except Exception as exc:
        if "0 rows" in str(exc) or "not found" in str(exc).lower():
            raise not_found("Asistencia", id)
        raise supabase_error(exc)


def update_asistencia(
    db: Client, id: str, data: AsistenciaUpdate, docente_id: str
) -> AsistenciaOut:
    payload = data.model_dump(exclude_none=True)
    if not payload:
        return get_asistencia(db, id)
    try:
        res = (
            db.table(ASIST_TABLE)
            .update(payload)
            .eq("id", id)
            .eq("docente_id", docente_id)   # solo el docente que lo creó
            .execute()
        )
        if not res.data:
            raise not_found("Asistencia", id)
        return AsistenciaOut(**res.data[0])
    except Exception as exc:
        raise supabase_error(exc)


# ── Reportes ──────────────────────────────────────────────────

def reporte_por_unidad(
    db: Client,
    unidad_id: str,
    fecha_inicio: date | None = None,
    fecha_fin: date | None = None,
) -> list[AsistenciaDetalle]:
    try:
        q = db.table("v_asistencias_completas").select("*").eq("unidad_id", unidad_id)
        if fecha_inicio:
            q = q.gte("fecha", fecha_inicio.isoformat())
        if fecha_fin:
            q = q.lte("fecha", fecha_fin.isoformat())
        res = q.order("fecha", desc=True).order("alumno").execute()
        return [AsistenciaDetalle(**r) for r in res.data]
    except Exception as exc:
        raise supabase_error(exc)


def resumen_por_alumno(
    db: Client,
    unidad_id: str,
    fecha_inicio: date | None = None,
    fecha_fin: date | None = None,
) -> list[ResumenAsistencia]:
    """Calcula totales y porcentaje de asistencia por alumno."""
    registros = reporte_por_unidad(db, unidad_id, fecha_inicio, fecha_fin)

    agrupado: dict[str, dict] = {}
    for r in registros:
        key = str(r.id)  # usamos el id del alumno via el detalle
        # agrupamos por (alumno, dni)
        clave = f"{r.alumno}|{r.dni}"
        if clave not in agrupado:
            agrupado[clave] = {
                "alumno_id":    r.id,
                "alumno":       r.alumno,
                "dni":          r.dni,
                "total": 0, "presentes": 0,
                "tardanzas": 0, "justificados": 0, "faltas": 0,
            }
        agrupado[clave]["total"] += 1
        match r.estado:
            case "P": agrupado[clave]["presentes"]    += 1
            case "T": agrupado[clave]["tardanzas"]    += 1
            case "J": agrupado[clave]["justificados"] += 1
            case "F": agrupado[clave]["faltas"]       += 1

    result = []
    for g in agrupado.values():
        asistidos = g["presentes"] + g["tardanzas"] + g["justificados"]
        pct = round(asistidos / g["total"] * 100, 1) if g["total"] > 0 else 0.0
        result.append(ResumenAsistencia(**g, porcentaje_asistencia=pct))
    return sorted(result, key=lambda x: x.alumno)

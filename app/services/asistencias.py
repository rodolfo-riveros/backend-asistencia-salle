from __future__ import annotations
from datetime import date
from typing import Any
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

def create_asignacion(db: Client, data: AsignacionCreate) -> AsignacionOut:
    """Crea una nueva asignación docente-unidad-periodo"""
    try:
        payload = {
            "docente_id": str(data.docente_id),
            "unidad_id":  str(data.unidad_id),
            "periodo_id": str(data.periodo_id),
        }
        res = db.table(ASIG_TABLE).insert(payload).execute()
        
        if not res.data:
            raise Exception("No se pudo crear la asignación")
            
        return AsignacionOut(**res.data[0])
    except Exception as exc:
        raise supabase_error(exc)


def list_asignaciones(
    db: Client, 
    docente_id: str | None = None, 
    periodo_nombre: str | None = None
) -> list[AsignacionDetalle]:
    """Lista asignaciones con filtros opcionales"""
    try:
        # Construir la consulta base con joins
        query = db.table(ASIG_TABLE).select("""
            id,
            docente_id,
            unidad_id,
            periodo_id,
            docentes (nombre),
            unidades_didacticas (
                nombre,
                semestre,
                programas_estudio (nombre)
            ),
            periodos_academicos (nombre)
        """)
        
        # Aplicar filtros
        if docente_id:
            query = query.eq("docente_id", docente_id)
        
        res = query.execute()
        
        result = []
        for r in res.data:
            # Filtrar por nombre de periodo si se especificó
            periodo_data = r.get("periodos_academicos", {}) or {}
            periodo_nombre_db = periodo_data.get("nombre")
            
            if periodo_nombre and periodo_nombre_db != periodo_nombre:
                continue
            
            # Extraer datos relacionados
            docente_nombre = r.get("docentes", {}).get("nombre") if r.get("docentes") else None
            unidad_data = r.get("unidades_didacticas", {}) or {}
            
            programa_nombre = None
            if unidad_data.get("programas_estudio"):
                programa_nombre = unidad_data["programas_estudio"].get("nombre")
            
            result.append(AsignacionDetalle(
                id=r["id"],
                docente_id=r["docente_id"],
                unidad_id=r["unidad_id"],
                periodo_id=r["periodo_id"],
                docente_nombre=docente_nombre,
                unidad_nombre=unidad_data.get("nombre"),
                semestre=str(unidad_data.get("semestre")) if unidad_data.get("semestre") else None,
                programa_nombre=programa_nombre,
                periodo_nombre=periodo_nombre_db
            ))
        
        return result
        
    except Exception as exc:
        raise supabase_error(exc)


def get_asignacion(db: Client, id: str) -> AsignacionDetalle:
    """Obtiene una asignación por ID con detalles"""
    try:
        res = db.table(ASIG_TABLE).select("""
            id,
            docente_id,
            unidad_id,
            periodo_id,
            docentes (nombre),
            unidades_didacticas (
                nombre,
                semestre,
                programas_estudio (nombre)
            ),
            periodos_academicos (nombre)
        """).eq("id", id).single().execute()
        
        if not res.data:
            raise not_found("Asignación", id)
        
        r = res.data
        docente_nombre = r.get("docentes", {}).get("nombre") if r.get("docentes") else None
        unidad_data = r.get("unidades_didacticas", {}) or {}
        periodo_data = r.get("periodos_academicos", {}) or {}
        
        programa_nombre = None
        if unidad_data.get("programas_estudio"):
            programa_nombre = unidad_data["programas_estudio"].get("nombre")
        
        return AsignacionDetalle(
            id=r["id"],
            docente_id=r["docente_id"],
            unidad_id=r["unidad_id"],
            periodo_id=r["periodo_id"],
            docente_nombre=docente_nombre,
            unidad_nombre=unidad_data.get("nombre"),
            semestre=str(unidad_data.get("semestre")) if unidad_data.get("semestre") else None,
            programa_nombre=programa_nombre,
            periodo_nombre=periodo_data.get("nombre")
        )
        
    except Exception as exc:
        if "0 rows" in str(exc) or "not found" in str(exc).lower():
            raise not_found("Asignación", id)
        raise supabase_error(exc)


def delete_asignacion(db: Client, id: str) -> None:
    """Elimina una asignación por ID"""
    try:
        # Verificar si existen asistencias relacionadas
        # Primero obtenemos la unidad_id de la asignación
        asignacion = db.table(ASIG_TABLE).select("unidad_id").eq("id", id).single().execute()
        
        if asignacion.data:
            # Verificar si hay asistencias para esa unidad
            asistencias = db.table(ASIST_TABLE).select("id").eq("unidad_id", asignacion.data["unidad_id"]).execute()
            if asistencias.data:
                raise bad_request("No se puede eliminar la asignación porque tiene registros de asistencia")
        
        res = db.table(ASIG_TABLE).delete().eq("id", id).execute()
        if not res.data:
            raise not_found("Asignación", id)
    except Exception as exc:
        raise supabase_error(exc)


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
            .eq("docente_id", docente_id)
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
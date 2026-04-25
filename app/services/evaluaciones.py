from __future__ import annotations
from collections import defaultdict
from supabase import Client

from app.schemas.evaluaciones import (
    IndicadorCreate, IndicadorUpdate, IndicadorOut,
    ConfigEvaluacionPayload, ConfigEvaluacionOut,
    EvaluacionCreate, EvaluacionUpdate, EvaluacionOut,
    GruposPayload, GrupoCreate, GrupoOut,
    CalificacionCreate, CalificacionOut,
    NotasGamificacionPayload,
    SaveAllPayload, RegistroAuxiliarOut, PromedioAlumno,
    TipoInstrumento,
)
from app.exceptions import not_found, supabase_error, bad_request

IND_TABLE   = "indicadores_logro"
EVAL_TABLE  = "evaluaciones"
CAL_TABLE   = "calificaciones"
GRUPO_TABLE = "evaluacion_grupos"
INTEG_TABLE = "evaluacion_grupo_integrantes"


# ══════════════════════════════════════════════════════════════════════
# POST /evaluaciones/config/
# Upsert indicador + insert evaluación en una sola llamada
# ══════════════════════════════════════════════════════════════════════

def upsert_config_evaluacion(db: Client, data: ConfigEvaluacionPayload) -> ConfigEvaluacionOut:
    """
    Paso 1 (Indicador) + Paso 2/3 (Instrumento):
      1. Upsert indicadores_logro por (unidad_id, periodo_id, codigo).
      2. Insert evaluación vinculada.
    Los criterios (configuracion_json) quedan guardados en Supabase.
    El frontend los leerá vía GET /config/{unidad_id}/{periodo_id} para
    pasárselos a la IA que genera las preguntas del quiz en Convex.
    """
    try:
        ind_payload = {
            "unidad_id":       str(data.unidad_id),
            "periodo_id":      str(data.periodo_id),
            "codigo":          data.indicador_codigo,
            "descripcion":     data.indicador_desc,
            "peso_porcentaje": data.indicador_peso,
        }
        ind_res = (
            db.table(IND_TABLE)
            .upsert(ind_payload, on_conflict="unidad_id,periodo_id,codigo")
            .execute()
        )
        if not ind_res.data:
            raise Exception("No se pudo crear/actualizar el indicador")
        indicador = IndicadorOut(**ind_res.data[0])

        eval_payload = {
            "indicador_id":      str(indicador.id),
            "periodo_id":        str(data.periodo_id),
            "nombre":            data.nombre,
            "tipo":              data.tipo.value,
            "peso_instrumento":  data.peso_instrumento,
            "puntaje_maximo":    data.puntaje_maximo,
            "configuracion_json": data.configuracion_json,
        }
        eval_res = db.table(EVAL_TABLE).insert(eval_payload).execute()
        if not eval_res.data:
            raise Exception("No se pudo crear la evaluación")
        evaluacion = EvaluacionOut(**eval_res.data[0])

        return ConfigEvaluacionOut(indicador=indicador, evaluacion=evaluacion)
    except Exception as exc:
        raise supabase_error(exc)


# ══════════════════════════════════════════════════════════════════════
# GET /evaluaciones/config/{unidad_id}/{periodo_id}
# JOIN evaluaciones + indicadores_logro
# ══════════════════════════════════════════════════════════════════════

def get_registro_auxiliar(db: Client, unidad_id: str, periodo_id: str) -> RegistroAuxiliarOut:
    try:
        eval_res = (
            db.table(EVAL_TABLE)
            .select("""
                id, nombre, tipo, peso_instrumento, puntaje_maximo,
                configuracion_json, created_at, periodo_id, indicador_id,
                indicadores_logro!inner (
                    id, codigo, descripcion, peso_porcentaje, unidad_id, periodo_id
                )
            """)
            .eq("indicadores_logro.unidad_id", unidad_id)
            .eq("indicadores_logro.periodo_id", periodo_id)
            .order("created_at")
            .execute()
        )

        indicadores_map: dict[str, IndicadorOut] = {}
        evaluaciones: list[EvaluacionOut] = []

        for r in eval_res.data:
            ind_data = r.get("indicadores_logro") or {}
            ind_id   = ind_data.get("id")
            if ind_id and ind_id not in indicadores_map:
                indicadores_map[ind_id] = IndicadorOut(
                    id=ind_id,
                    unidad_id=ind_data["unidad_id"],
                    periodo_id=ind_data["periodo_id"],
                    codigo=ind_data["codigo"],
                    descripcion=ind_data["descripcion"],
                    peso_porcentaje=ind_data["peso_porcentaje"],
                )
            evaluaciones.append(EvaluacionOut(
                id=r["id"],
                indicador_id=r.get("indicador_id"),
                periodo_id=r.get("periodo_id"),
                nombre=r["nombre"],
                tipo=r["tipo"],
                peso_instrumento=r["peso_instrumento"],
                puntaje_maximo=r["puntaje_maximo"],
                configuracion_json=r.get("configuracion_json"),
                created_at=r.get("created_at"),
                indicador_codigo=ind_data.get("codigo"),
                indicador_desc=ind_data.get("descripcion"),
                indicador_peso=ind_data.get("peso_porcentaje"),
            ))

        indicadores = list(indicadores_map.values())
        eval_ids    = [str(e.id) for e in evaluaciones]

        grupos:         list[GrupoOut]        = []
        calificaciones: list[CalificacionOut] = []
        for eid in eval_ids:
            grupos.extend(list_grupos(db, eid))
            calificaciones.extend(list_calificaciones(db, eid))

        promedios = _calcular_promedios(db, indicadores, evaluaciones, calificaciones)

        return RegistroAuxiliarOut(
            unidad_id=unidad_id,    # type: ignore
            periodo_id=periodo_id,  # type: ignore
            indicadores=indicadores,
            evaluaciones=evaluaciones,
            grupos=grupos,
            calificaciones=calificaciones,
            promedios=promedios,
        )
    except Exception as exc:
        raise supabase_error(exc)


# ══════════════════════════════════════════════════════════════════════
# INDICADORES CRUD
# ══════════════════════════════════════════════════════════════════════

def create_indicador(db: Client, data: IndicadorCreate) -> IndicadorOut:
    try:
        payload = data.model_dump()
        payload["unidad_id"]  = str(payload["unidad_id"])
        payload["periodo_id"] = str(payload["periodo_id"])
        res = db.table(IND_TABLE).insert(payload).execute()
        if not res.data:
            raise Exception("No se pudo crear el indicador")
        return IndicadorOut(**res.data[0])
    except Exception as exc:
        raise supabase_error(exc)


def list_indicadores(db: Client, unidad_id: str, periodo_id: str) -> list[IndicadorOut]:
    try:
        res = (
            db.table(IND_TABLE)
            .select("*")
            .eq("unidad_id", unidad_id)
            .eq("periodo_id", periodo_id)
            .order("codigo")
            .execute()
        )
        return [IndicadorOut(**r) for r in res.data]
    except Exception as exc:
        raise supabase_error(exc)


def update_indicador(db: Client, id: str, data: IndicadorUpdate) -> IndicadorOut:
    payload = data.model_dump(exclude_none=True)
    if not payload:
        raise bad_request("Sin campos a actualizar")
    _check_no_calificaciones_for_indicador(db, id)
    try:
        res = db.table(IND_TABLE).update(payload).eq("id", id).execute()
        if not res.data:
            raise not_found("Indicador", id)
        return IndicadorOut(**res.data[0])
    except Exception as exc:
        raise supabase_error(exc)


def delete_indicador(db: Client, id: str) -> None:
    _check_no_calificaciones_for_indicador(db, id)
    try:
        res = db.table(IND_TABLE).delete().eq("id", id).execute()
        if not res.data:
            raise not_found("Indicador", id)
    except Exception as exc:
        raise supabase_error(exc)


def _check_no_calificaciones_for_indicador(db: Client, indicador_id: str) -> None:
    try:
        evals = db.table(EVAL_TABLE).select("id").eq("indicador_id", indicador_id).execute()
        if not evals.data:
            return
        for e in evals.data:
            cals = db.table(CAL_TABLE).select("id").eq("evaluacion_id", e["id"]).limit(1).execute()
            if cals.data:
                raise bad_request(
                    "No se puede modificar/eliminar el indicador porque ya tiene calificaciones."
                )
    except Exception as exc:
        raise supabase_error(exc)


# ══════════════════════════════════════════════════════════════════════
# EVALUACIONES CRUD
# ══════════════════════════════════════════════════════════════════════

def create_evaluacion(db: Client, data: EvaluacionCreate) -> EvaluacionOut:
    try:
        payload = data.model_dump()
        payload["indicador_id"] = str(payload["indicador_id"])
        payload["periodo_id"]   = str(payload["periodo_id"])
        payload["tipo"] = payload["tipo"].value if hasattr(payload["tipo"], "value") else payload["tipo"]
        res = db.table(EVAL_TABLE).insert(payload).execute()
        if not res.data:
            raise Exception("No se pudo crear la evaluación")
        return EvaluacionOut(**res.data[0])
    except Exception as exc:
        raise supabase_error(exc)


def get_evaluacion(db: Client, id: str) -> EvaluacionOut:
    try:
        res = db.table(EVAL_TABLE).select("*").eq("id", id).single().execute()
        if not res.data:
            raise not_found("Evaluación", id)
        return EvaluacionOut(**res.data)
    except Exception as exc:
        raise supabase_error(exc)


def list_evaluaciones(db: Client, indicador_id: str) -> list[EvaluacionOut]:
    try:
        res = (
            db.table(EVAL_TABLE)
            .select("*")
            .eq("indicador_id", indicador_id)
            .order("created_at")
            .execute()
        )
        return [EvaluacionOut(**r) for r in res.data]
    except Exception as exc:
        raise supabase_error(exc)


def update_evaluacion(db: Client, id: str, data: EvaluacionUpdate) -> EvaluacionOut:
    payload = data.model_dump(exclude_none=True)
    if not payload:
        raise bad_request("Sin campos a actualizar")
    cals = db.table(CAL_TABLE).select("id").eq("evaluacion_id", id).limit(1).execute()
    if cals.data and "tipo" in payload:
        raise bad_request("No se puede cambiar el tipo si ya hay calificaciones.")
    try:
        res = db.table(EVAL_TABLE).update(payload).eq("id", id).execute()
        if not res.data:
            raise not_found("Evaluación", id)
        return EvaluacionOut(**res.data[0])
    except Exception as exc:
        raise supabase_error(exc)


def delete_evaluacion(db: Client, id: str) -> None:
    cals = db.table(CAL_TABLE).select("id").eq("evaluacion_id", id).limit(1).execute()
    if cals.data:
        raise bad_request("No se puede eliminar porque ya tiene calificaciones.")
    try:
        res = db.table(EVAL_TABLE).delete().eq("id", id).execute()
        if not res.data:
            raise not_found("Evaluación", id)
    except Exception as exc:
        raise supabase_error(exc)


# ══════════════════════════════════════════════════════════════════════
# GRUPOS — POST /evaluaciones/grupos/
# ══════════════════════════════════════════════════════════════════════

def guardar_grupos(db: Client, payload: GruposPayload) -> list[GrupoOut]:
    """Idempotente: elimina grupos previos y recrea."""
    try:
        evaluacion_id = str(payload.evaluacion_id)
        viejos = db.table(GRUPO_TABLE).select("id").eq("evaluacion_id", evaluacion_id).execute()
        for g in (viejos.data or []):
            db.table(INTEG_TABLE).delete().eq("grupo_id", g["id"]).execute()
        db.table(GRUPO_TABLE).delete().eq("evaluacion_id", evaluacion_id).execute()

        result: list[GrupoOut] = []
        for grupo_in in payload.grupos:
            grupo_res = db.table(GRUPO_TABLE).insert({
                "evaluacion_id": evaluacion_id,
                "nombre_grupo":  grupo_in.nombre_grupo,
            }).execute()
            grupo_id = grupo_res.data[0]["id"]
            for alumno_id in grupo_in.integrantes:
                db.table(INTEG_TABLE).insert({
                    "grupo_id":  grupo_id,
                    "alumno_id": str(alumno_id),
                }).execute()
            result.append(GrupoOut(
                id=grupo_id,
                evaluacion_id=evaluacion_id,   # type: ignore
                nombre_grupo=grupo_in.nombre_grupo,
                created_at=grupo_res.data[0].get("created_at"),
                integrantes=grupo_in.integrantes,
            ))
        return result
    except Exception as exc:
        raise supabase_error(exc)


def create_grupo(db: Client, data: GrupoCreate) -> GrupoOut:
    try:
        res = db.table(GRUPO_TABLE).insert({
            "evaluacion_id": str(data.evaluacion_id),
            "nombre_grupo":  data.nombre_grupo,
        }).execute()
        if not res.data:
            raise Exception("No se pudo crear el grupo")
        return GrupoOut(**res.data[0], integrantes=[])
    except Exception as exc:
        raise supabase_error(exc)


def add_integrante(db: Client, grupo_id: str, alumno_id: str) -> None:
    try:
        db.table(INTEG_TABLE).insert({"grupo_id": grupo_id, "alumno_id": alumno_id}).execute()
    except Exception as exc:
        raise supabase_error(exc)


def list_grupos(db: Client, evaluacion_id: str) -> list[GrupoOut]:
    try:
        res = (
            db.table(GRUPO_TABLE)
            .select("*, evaluacion_grupo_integrantes(alumno_id)")
            .eq("evaluacion_id", evaluacion_id)
            .execute()
        )
        result = []
        for g in res.data:
            integrantes = [i["alumno_id"] for i in (g.get("evaluacion_grupo_integrantes") or [])]
            result.append(GrupoOut(
                id=g["id"],
                evaluacion_id=g["evaluacion_id"],
                nombre_grupo=g["nombre_grupo"],
                created_at=g.get("created_at"),
                integrantes=integrantes,
            ))
        return result
    except Exception as exc:
        raise supabase_error(exc)


def _get_grupo_de_alumno(db: Client, evaluacion_id: str, alumno_id: str) -> list[str] | None:
    try:
        integ_res = db.table(INTEG_TABLE).select("grupo_id").eq("alumno_id", alumno_id).execute()
        if not integ_res.data:
            return None
        grupo_ids = [i["grupo_id"] for i in integ_res.data]
        grupos_eval = (
            db.table(GRUPO_TABLE)
            .select("id")
            .eq("evaluacion_id", evaluacion_id)
            .in_("id", grupo_ids)
            .execute()
        )
        if not grupos_eval.data:
            return None
        grupo_id = grupos_eval.data[0]["id"]
        todos = db.table(INTEG_TABLE).select("alumno_id").eq("grupo_id", grupo_id).execute()
        return [i["alumno_id"] for i in todos.data]
    except Exception as exc:
        raise supabase_error(exc)


# ══════════════════════════════════════════════════════════════════════
# CALIFICAR — POST /evaluaciones/calificar/
# ══════════════════════════════════════════════════════════════════════

def upsert_calificacion(db: Client, data: CalificacionCreate) -> list[CalificacionOut]:
    try:
        eval_res = (
            db.table(EVAL_TABLE)
            .select("tipo,puntaje_maximo")
            .eq("id", str(data.evaluacion_id))
            .single()
            .execute()
        )
        if not eval_res.data:
            raise not_found("Evaluación", str(data.evaluacion_id))

        tipo        = eval_res.data["tipo"]
        puntaje_max = eval_res.data.get("puntaje_maximo") or 20

        puntaje_recibido = float(data.puntaje)

        if puntaje_recibido > puntaje_max:
            raise bad_request(f"Puntaje {puntaje_recibido} supera el máximo ({puntaje_max}).")

        puntaje_final = puntaje_recibido

        # Para QUIZZ: si el frontend ya calculó la nota, la usa directo.
        if tipo == TipoInstrumento.QUIZZ and data.detalles_json and puntaje_recibido == 0:
            aciertos        = data.detalles_json.get("aciertos", 0)
            total_preguntas = data.detalles_json.get("total_preguntas", 1)
            if aciertos > 0:
                puntaje_final = round((aciertos / max(total_preguntas, 1)) * puntaje_max, 2)

        alumnos_ids = [str(data.alumno_id)]
        if tipo == TipoInstrumento.GRUPAL:
            companeros = _get_grupo_de_alumno(db, str(data.evaluacion_id), str(data.alumno_id))
            if companeros:
                alumnos_ids = companeros

        resultados: list[CalificacionOut] = []
        for alumno_id in alumnos_ids:
            row = {
                "evaluacion_id": str(data.evaluacion_id),
                "alumno_id":     alumno_id,
                "puntaje":       puntaje_final,
                "observacion":   data.observacion,
                "detalles_json": data.detalles_json,
            }
            res = (
                db.table(CAL_TABLE)
                .upsert(row, on_conflict="evaluacion_id,alumno_id")
                .execute()
            )
            if res.data:
                resultados.append(CalificacionOut(**res.data[0]))
        return resultados
    except Exception as exc:
        raise supabase_error(exc)


# ══════════════════════════════════════════════════════════════════════
# NOTAS GAMIFICACIÓN — POST /evaluaciones/notas-gamificacion/
# Llamado por el frontend Convex al terminar el quiz
# ══════════════════════════════════════════════════════════════════════

def bulk_notas_gamificacion(db: Client, payload: NotasGamificacionPayload) -> dict:
    """
    Bulk upsert de calificaciones enviadas por el frontend al cerrar el quiz en Convex.
    Espera: { evaluacion_id, notas: [{alumno_id, aciertos, total_preguntas}] }
    """
    eval_res = (
        db.table(EVAL_TABLE)
        .select("puntaje_maximo")
        .eq("id", str(payload.evaluacion_id))
        .single()
        .execute()
    )
    if not eval_res.data:
        raise not_found("Evaluación", str(payload.evaluacion_id))
    puntaje_max = eval_res.data.get("puntaje_maximo") or 20

    rows = []
    for nota in payload.notas:
        alumno_id       = nota.get("alumno_id")
        aciertos        = nota.get("aciertos", 0)
        total_preguntas = nota.get("total_preguntas", 1)
        if not alumno_id:
            continue
        puntaje = round((aciertos / max(total_preguntas, 1)) * puntaje_max, 2)
        rows.append({
            "evaluacion_id": str(payload.evaluacion_id),
            "alumno_id":     alumno_id,
            "puntaje":       puntaje,
            "detalles_json": {"aciertos": aciertos, "total_preguntas": total_preguntas},
        })

    if not rows:
        return {"guardadas": 0}

    res = db.table(CAL_TABLE).upsert(rows, on_conflict="evaluacion_id,alumno_id").execute()
    return {"guardadas": len(res.data or [])}


def list_calificaciones(db: Client, evaluacion_id: str) -> list[CalificacionOut]:
    try:
        res = db.table(CAL_TABLE).select("*").eq("evaluacion_id", evaluacion_id).execute()
        return [CalificacionOut(**r) for r in res.data]
    except Exception as exc:
        raise supabase_error(exc)


def get_calificacion(db: Client, id: str) -> CalificacionOut:
    try:
        res = db.table(CAL_TABLE).select("*").eq("id", id).single().execute()
        if not res.data:
            raise not_found("Calificación", id)
        return CalificacionOut(**res.data)
    except Exception as exc:
        raise supabase_error(exc)


# ══════════════════════════════════════════════════════════════════════
# PROMEDIOS PONDERADOS
# ══════════════════════════════════════════════════════════════════════

def _calcular_promedios(
    db: Client,
    indicadores: list[IndicadorOut],
    evaluaciones: list[EvaluacionOut],
    calificaciones: list[CalificacionOut],
) -> list[PromedioAlumno]:
    evals_por_ind: dict[str, list[EvaluacionOut]] = defaultdict(list)
    for e in evaluaciones:
        if e.indicador_id:
            evals_por_ind[str(e.indicador_id)].append(e)

    cal_map: dict[tuple, float] = {}
    for c in calificaciones:
        cal_map[(str(c.evaluacion_id), str(c.alumno_id))] = c.puntaje

    alumno_ids = list({str(c.alumno_id) for c in calificaciones})
    if not alumno_ids:
        return []

    alumnos_res = db.table("alumnos").select("id,nombre").in_("id", alumno_ids).execute()
    nombre_map  = {r["id"]: r["nombre"] for r in alumnos_res.data}

    resultados: list[PromedioAlumno] = []
    for alumno_id in alumno_ids:
        promedio_total = 0.0
        detalle        = []
        for ind in indicadores:
            evals = evals_por_ind.get(str(ind.id), [])
            if not evals:
                continue
            suma_pesos     = sum(e.peso_instrumento for e in evals) or 1
            nota_indicador = 0.0
            for e in evals:
                puntaje   = cal_map.get((str(e.id), alumno_id), 0.0)
                maximo    = e.puntaje_maximo or 20
                nota_norm = (puntaje / maximo) * 20
                peso_rel  = e.peso_instrumento / suma_pesos
                nota_indicador += peso_rel * nota_norm
            promedio_total += (ind.peso_porcentaje / 100) * nota_indicador
            detalle.append({
                "indicador":       ind.codigo,
                "nota_indicador":  round(nota_indicador, 2),
                "peso_porcentaje": ind.peso_porcentaje,
            })
        resultados.append(PromedioAlumno(
            alumno_id=alumno_id,  # type: ignore
            alumno_nombre=nombre_map.get(alumno_id, alumno_id),
            promedio=round(promedio_total, 2),
            detalle=detalle,
        ))
    return sorted(resultados, key=lambda x: x.alumno_nombre)


# ══════════════════════════════════════════════════════════════════════
# SAVE-ALL (upsert masivo legacy)
# ══════════════════════════════════════════════════════════════════════

def save_all(db: Client, payload: SaveAllPayload) -> dict:
    stats = {"indicadores": 0, "evaluaciones": 0, "calificaciones": 0}
    for ind_data in payload.indicadores:
        ind_data["unidad_id"]  = str(payload.unidad_id)
        ind_data["periodo_id"] = str(payload.periodo_id)
        ind_id = ind_data.pop("id", None)
        if ind_id:
            db.table(IND_TABLE).upsert({"id": ind_id, **ind_data}).execute()
        else:
            db.table(IND_TABLE).insert(ind_data).execute()
        stats["indicadores"] += 1
    for eval_data in payload.evaluaciones:
        eval_data["periodo_id"] = str(payload.periodo_id)
        eval_id = eval_data.pop("id", None)
        if eval_id:
            db.table(EVAL_TABLE).upsert({"id": eval_id, **eval_data}).execute()
        else:
            db.table(EVAL_TABLE).insert(eval_data).execute()
        stats["evaluaciones"] += 1
    for cal_data in payload.calificaciones:
        upsert_calificacion(db, CalificacionCreate(**cal_data))
        stats["calificaciones"] += 1
    return stats

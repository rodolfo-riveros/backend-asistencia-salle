from fastapi import HTTPException, status


def not_found(entity: str, id: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"{entity} con id '{id}' no encontrado",
    )


def conflict(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


def bad_request(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def supabase_error(exc: Exception) -> HTTPException:
    """Convierte errores de Supabase en HTTPException legibles."""
    msg = str(exc)
    # Violación de unicidad
    if "duplicate key" in msg or "unique" in msg.lower():
        return conflict("Ya existe un registro con esos datos")
    # FK violation
    if "foreign key" in msg.lower():
        return bad_request("Referencia a un recurso que no existe")
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Error en base de datos: {msg}",
    )

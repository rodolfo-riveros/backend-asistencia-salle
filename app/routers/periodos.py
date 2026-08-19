from fastapi import APIRouter, Query, HTTPException
from app.auth import CurrentAdmin, CurrentUser
from app.database import get_admin_client, get_client
# Asegúrate de tener estos esquemas creados, si no, usa dict temporalmente
# from app.schemas import PeriodoCreate, PeriodoOut 

router = APIRouter(prefix="/periodos", tags=["Periodos"])

@router.get("/")
def listar_periodos(_: CurrentUser):
    # Esto asume que tienes una tabla 'periodos_academicos' en Supabase
    client = get_client()
    response = client.table("periodos_academicos").select("*").order("nombre").execute()
    return response.data

@router.post("/", status_code=201)
def crear_periodo(data: dict, _: CurrentAdmin):
    client = get_admin_client()
    if data.get("es_activo"):
        client.table("periodos_academicos").update({"es_activo": False}).neq("id", "00000000-0000-0000-0000-000000000000").execute()
    response = client.table("periodos_academicos").insert(data).execute()
    return response.data[0]

@router.patch("/{id}")
def actualizar_periodo(id: str, data: dict, _: CurrentAdmin):
    client = get_admin_client()
    if data.get("es_activo") is True:
        client.table("periodos_academicos").update({"es_activo": False}).neq("id", id).execute()
    response = client.table("periodos_academicos").update(data).eq("id", id).execute()
    return response.data[0]

@router.delete("/{id}", status_code=204)
def eliminar_periodo(id: str, _: CurrentAdmin):
    client = get_admin_client()
    client.table("periodos_academicos").delete().eq("id", id).execute()
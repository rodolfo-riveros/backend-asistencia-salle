# Sistema de Asistencia — FastAPI Backend

API REST para registro de asistencia en instituto de educación superior tecnológico.
Conectada a Supabase (PostgreSQL + Auth + RLS).

---

## Estructura del proyecto

```
asistencia_api/
├── main.py                      # Punto de entrada uvicorn
├── requirements.txt
├── .env.example
└── app/
    ├── main.py                  # FastAPI app, routers, middleware
    ├── config.py                # Settings con pydantic-settings
    ├── database.py              # Clientes Supabase (anon + service_role)
    ├── auth.py                  # Validación JWT + dependencias de rol
    ├── exceptions.py            # Helpers de errores HTTP
    ├── schemas/
    │   ├── programas.py
    │   ├── unidades.py
    │   ├── docentes.py
    │   ├── alumnos.py
    │   └── asistencias.py      # Asignaciones + Asistencias + Reportes
    ├── services/
    │   ├── programas.py
    │   ├── unidades.py
    │   ├── docentes.py
    │   ├── alumnos.py
    │   └── asistencias.py      # Lógica de asignaciones + asistencias
    └── routers/
        ├── programas.py
        ├── unidades.py
        ├── docentes.py
        ├── alumnos.py
        ├── asignaciones.py
        ├── asistencias.py
        └── me.py               # Endpoints del docente autenticado
```

---

## Instalación y configuración

### 1. Clonar e instalar dependencias

```bash
cd asistencia_api
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env
```

Editar `.env` con los valores de tu proyecto Supabase:

| Variable | Dónde encontrarla |
|---|---|
| `SUPABASE_URL` | Dashboard → Settings → API → Project URL |
| `SUPABASE_ANON_KEY` | Dashboard → Settings → API → anon public |
| `SUPABASE_SERVICE_ROLE_KEY` | Dashboard → Settings → API → service_role |
| `SUPABASE_JWT_SECRET` | Dashboard → Settings → API → JWT Secret |

### 3. Levantar el servidor

```bash
python main.py
# o directamente:
uvicorn app.main:app --reload --port 8000
```

Documentación interactiva: http://localhost:8000/docs

---

## Roles y autenticación

El sistema maneja dos roles definidos en el **User Metadata** de Supabase Auth:

| Rol | Acceso |
|---|---|
| `admin` | CRUD completo de todas las entidades |
| `docente` | Solo puede registrar asistencia de sus unidades asignadas |

### Asignar rol a un usuario

En Supabase Dashboard → Authentication → Users → editar usuario → User Metadata:

```json
{ "role": "admin" }
```
o
```json
{ "role": "docente" }
```

### Usar el token en los requests

```http
Authorization: Bearer <JWT de Supabase Auth>
```

---

## Endpoints principales

### Flujo del docente (pase de lista)

```
1. GET  /api/v1/me/asignaciones?periodo=2025-I
   → Ver mis cursos del periodo

2. GET  /api/v1/me/unidades/{unidad_id}/alumnos
   → Ver la lista de alumnos del curso seleccionado

3. POST /api/v1/asistencias/pase-lista
   → Registrar el pase de lista completo
```

**Body del pase de lista:**
```json
{
  "unidad_id": "uuid-de-la-unidad",
  "fecha": "2025-06-10",
  "registros": [
    { "alumno_id": "uuid-1", "estado": "P" },
    { "alumno_id": "uuid-2", "estado": "T", "observacion": "Llegó 10 min tarde" },
    { "alumno_id": "uuid-3", "estado": "F" },
    { "alumno_id": "uuid-4", "estado": "J", "observacion": "Presentó justificación médica" }
  ]
}
```

**Estados:** `P` Presente · `T` Tarde · `J` Justificado · `F` Falta

### Reportes

```
GET /api/v1/asistencias/reporte/unidad/{unidad_id}?fecha_inicio=2025-03-01&fecha_fin=2025-07-31
GET /api/v1/asistencias/reporte/resumen/{unidad_id}
```

### Admin — CRUD

```
GET|POST        /api/v1/programas/
GET|PATCH|DELETE /api/v1/programas/{id}

GET|POST        /api/v1/unidades/
GET|PATCH|DELETE /api/v1/unidades/{id}
GET             /api/v1/unidades/{id}/alumnos

GET|POST        /api/v1/docentes/
GET|PATCH|DELETE /api/v1/docentes/{id}

GET|POST        /api/v1/alumnos/
GET|PATCH|DELETE /api/v1/alumnos/{id}
GET             /api/v1/alumnos/dni/{dni}

GET|POST        /api/v1/asignaciones/
GET|DELETE      /api/v1/asignaciones/{id}
```

---

## Notas importantes

- El cliente `get_client()` usa la **anon key** y respeta las políticas RLS de Supabase.
- El cliente `get_admin_client()` usa la **service_role key** y bypasea RLS — solo se usa en operaciones de admin.
- El endpoint `/pase-lista` usa **upsert**, por lo que si se envía dos veces el mismo día sobreescribe los registros anteriores (útil si el docente corrige).
- El `id` del docente debe coincidir con el UUID del usuario en `auth.users` de Supabase.
# backend-asistencia-salle

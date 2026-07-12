import httpx
import json
import re
from app.config import get_settings

SYSTEM_PROMPT = """
Eres un asistente que genera preguntas de evaluación académica en español.
Genera preguntas de opción múltiple (4 opciones) basadas ESTRICTAMENTE en el CONTENIDO ACADÉMICO del texto proporcionado.
IGNORA cualquier metadato del archivo (nombre de archivo, software creador, versión, autor, fechas, etc.).
Cada pregunta debe medir comprensión del tema académico, no sobre el formato del documento.
Cada pregunta debe tener: pregunta, 4 opciones, y el índice de la respuesta correcta (0-3).
Responde ÚNICAMENTE con JSON válido, sin markdown ni explicaciones.
El JSON debe tener esta estructura exacta:
{"preguntas": [{"pregunta": "...", "opciones": ["a) ...", "b) ...", "c) ...", "d) ..."], "correcta": 0}]}
Genera exactamente la cantidad solicitada de preguntas.
""".strip()


async def generar_preguntas_desde_texto(
    texto_markdown: str,
    cantidad: int = 5,
) -> list[dict]:
    """Llama a Gemini 2.5 Flash (API directa) para generar preguntas desde texto."""
    settings = get_settings()
    api_key = settings.gemini_api_key

    if not api_key:
        raise RuntimeError("GEMINI_API_KEY no configurada en .env del backend")

    user_prompt = f"Genera {cantidad} preguntas basadas en este contenido:\n\n{texto_markdown[:8000]}"

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": f"{SYSTEM_PROMPT}\n\n{user_prompt}"}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.7,
            "topP": 0.95,
            "maxOutputTokens": 8192,
        }
    }

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()

    text = data["candidates"][0]["content"]["parts"][0]["text"]

    json_match = re.search(r"\{.*\}", text, re.DOTALL)
    if json_match:
        text = json_match.group()

    result = json.loads(text)
    return result.get("preguntas", result) if isinstance(result, dict) else result

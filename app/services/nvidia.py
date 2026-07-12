import asyncio
from openai import AsyncOpenAI
from app.config import get_settings


SYSTEM_PROMPT = """
Eres un asistente que genera preguntas de evaluación académica.
Genera preguntas de opción múltiple (4 opciones) basadas ESTRICTAMENTE en el CONTENIDO ACADÉMICO del texto proporcionado.
IGNORA cualquier metadato del archivo (nombre de archivo, software creador, versión, autor, fechas, etc.).
Cada pregunta debe medir comprensión del tema, no sobre el formato del documento.
Cada pregunta debe tener: pregunta, 4 opciones (a, b, c, d), y el índice de la respuesta correcta (0-3).
Responde ÚNICAMENTE con JSON válido, sin markdown ni explicaciones.
El JSON debe tener esta estructura exacta:
{"preguntas": [{"pregunta": "...", "opciones": ["a) ...", "b) ...", "c) ...", "d) ..."], "correcta": 0}]}
Genera exactamente 5 preguntas a menos que se indique lo contrario.
""".strip()


async def generar_preguntas_desde_texto(
    texto_markdown: str,
    cantidad: int = 5,
) -> list[dict]:
    """Llama a NVIDIA DeepSeek v4 Pro para generar preguntas desde texto."""
    settings = get_settings()
    api_key = settings.nvidia_api_key

    if not api_key:
        raise RuntimeError("NVIDIA_API_KEY no configurada en .env")

    client = AsyncOpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=api_key,
        timeout=60,
    )

    user_prompt = f"Genera {cantidad} preguntas basadas en este contenido:\n\n{texto_markdown[:8000]}"

    completion = await client.chat.completions.create(
        model="deepseek-ai/deepseek-v4-pro",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=1,
        top_p=0.95,
        max_tokens=16384,
        extra_body={"chat_template_kwargs": {"thinking": False}},
    )

    content = completion.choices[0].message.content

    import re
    import json as j

    json_match = re.search(r"\{.*\}", content, re.DOTALL)
    if json_match:
        content = json_match.group()

    result = j.loads(content)
    return result.get("preguntas", result) if isinstance(result, dict) else result

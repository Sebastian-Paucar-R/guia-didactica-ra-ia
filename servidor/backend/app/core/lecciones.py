"""Relación lección (id de la app Flutter) -> tema del sílabo, para que una pregunta hecha dentro de una lección
recupere contexto priorizando ese tema (ver RAGService._flujo y api/v1/endpoints/chat.py, campo `leccion_id`).

`configuracion/lecciones.json` es la única fuente; a diferencia de `core/silabo.py` (que falla el arranque si el
YAML es inválido: el sílabo es central a todo el filtro), una entrada de `lecciones.json` que apunte a un
`tema_id` inexistente solo se ignora con un aviso — una lección no resuelta no debe tumbar el servidor, porque
el resto del tutor funciona perfectamente sin ella (cae al filtro de pertinencia normal)."""
import json
from functools import lru_cache
from pathlib import Path

from app.core import silabo
from app.core.config import settings


@lru_cache(maxsize=2)
def _cargar(ruta: str) -> dict[str, str]:
    archivo = Path(ruta)
    if not archivo.is_file():
        return {}
    datos = json.loads(archivo.read_text(encoding="utf-8"))
    crudo = datos.get("lecciones", {})
    validos = {t.id for t in silabo.temas()}
    resultado = {}
    for leccion_id, tema_id in crudo.items():
        if str(tema_id) in validos:
            resultado[str(leccion_id)] = str(tema_id)
        else:
            print(f"[LECCIONES] '{leccion_id}' apunta al tema '{tema_id}', que no existe en el sílabo; se ignora.")
    return resultado


def resolver_leccion(leccion_id: str | None, ruta: Path | str | None = None):
    """El Tema del sílabo asociado a `leccion_id`, o None si no se conoce (leccion_id vacío, no está en
    lecciones.json, o el sílabo cambió y el tema ya no existe). Devuelve un `silabo.Tema` completo, no solo el
    id, para que quien llama tenga nombre/unidad/archivos sin una segunda consulta."""
    if not leccion_id:
        return None
    mapa = _cargar(str(ruta or settings.LECCIONES_PATH))
    tema_id = mapa.get(leccion_id)
    if tema_id is None:
        return None
    return next((t for t in silabo.temas() if t.id == tema_id), None)

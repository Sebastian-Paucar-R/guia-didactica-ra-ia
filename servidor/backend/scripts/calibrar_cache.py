"""Mide la similitud coseno (embeddings reales de settings.MODELO_EMBEDDINGS) entre pares de preguntas y dice si el caché
semántico los daría por la misma pregunta con el umbral actual (CACHE_UMBRAL_SIMILITUD) y sus salvaguardas.

Uso (desde servidor/backend):  python scripts/calibrar_cache.py
No usa el LLM ni toca base_vectorial/ ni cache_respuestas.db. Sirve para elegir CACHE_UMBRAL_SIMILITUD:
los pares "MISMA" deberían acertar y los "DISTINTA" no.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings  # noqa: E402
from app.core.embeddings import crear_embeddings  # noqa: E402
from app.services.cache_service import huella_de, intencion_de  # noqa: E402

BASE = "¿Qué es la norma ISO 25010?"

# (etiqueta, pregunta A, pregunta B): MISMA = debería salir del caché; DISTINTA = no debería
PARES = [
    ("MISMA  (cosmético)", BASE, "¿Qué es la ISO 25010?"),
    ("MISMA  (cosmético)", BASE, "qué es la norma iso 25010"),
    ("MISMA  (cosmético)", BASE, "¿Qué es la norma ISO/IEC 25010?"),
    ("MISMA  (cosmético)", BASE, "¿Qué es exactamente la norma ISO 25010?"),
    ("MISMA  (cosmético)", BASE, "Oye, ¿qué es la norma ISO 25010?"),
    ("MISMA  (cosmético)", BASE, "¿Qué es la norma ISO 25010, por favor?"),
    ("MISMA  (reformulada)", BASE, "¿Podrías explicarme qué es ISO 25010?"),
    ("MISMA  (reformulada)", BASE, "Explícame la ISO 25010"),
    ("MISMA  (reformulada)", BASE, "Dime en qué consiste la norma ISO/IEC 25010"),
    ("MISMA  (reformulada)", "¿Cuáles son los principios de gestión de la calidad de ISO 9001?",
     "¿Qué principios de calidad establece ISO 9001?"),
    ("MISMA  (reformulada)", "¿Cuáles son los principios de gestión de la calidad de ISO 9001?",
     "Cuáles son los principios de la ISO 9001"),
    ("DISTINTA (otra norma)", "¿Qué es la norma ISO 9001?", "¿Qué es la norma ISO 27001?"),
    ("DISTINTA (otra norma)", BASE, "¿Qué es la norma ISO 12207?"),
    ("DISTINTA (otra norma)", "¿Cuáles son los requisitos de ISO 9001?", "¿Cuáles son los requisitos de ISO 27001?"),
    ("DISTINTA (negación)", "¿Qué es ISO 25010?", "¿Qué no es ISO 25010?"),
    ("DISTINTA (otro modo)", BASE, "Explícame con un ejemplo qué es la norma ISO 25010"),
    ("DISTINTA (otro modo)", BASE, "Resuélveme el ejercicio sobre la norma ISO 25010"),
    ("DISTINTA (otra pregunta)", BASE, "¿Cuáles son las características de la norma ISO 25010?"),
    ("DISTINTA (otro tema)", "¿Qué es la seguridad de la información?", "¿Qué es la seguridad del software?"),
]


def main():
    embeddings = crear_embeddings()
    print(f"Modelo de embeddings: {settings.MODELO_EMBEDDINGS}")
    umbral = settings.CACHE_UMBRAL_SIMILITUD
    print(f"\nUmbral actual: {umbral}   (columnas: similitud | ¿pasa las salvaguardas? | ¿acierto de caché?)\n")
    resumen = {"MISMA": [0, 0], "DISTINTA": [0, 0]}      # [aciertos de caché, total]
    for etiqueta, a, b in PARES:
        va, vb = (np.array(embeddings.embed_query(t)) for t in (a, b))
        similitud = float(va @ vb / (np.linalg.norm(va) * np.linalg.norm(vb)))
        guardas = intencion_de(a) == intencion_de(b) and huella_de(a) == huella_de(b)
        acierto = guardas and similitud >= umbral
        grupo = etiqueta.split()[0]
        resumen[grupo][0] += acierto
        resumen[grupo][1] += 1
        solo_similitud = "  (sin salvaguardas SÍ sería acierto)" if grupo == "DISTINTA" and not acierto \
            and similitud >= umbral else ""
        print(f"{similitud:.3f} | guardas={'sí' if guardas else 'NO'} | {'ACIERTO' if acierto else 'fallo  '} | "
              f"{etiqueta:<24} {a!r} ~ {b!r}{solo_similitud}")
    print(f"\nMISMA pregunta que acierta:   {resumen['MISMA'][0]}/{resumen['MISMA'][1]}")
    print(f"DISTINTA que se confunde:     {resumen['DISTINTA'][0]}/{resumen['DISTINTA'][1]}  (debe ser 0)")


if __name__ == "__main__":
    main()

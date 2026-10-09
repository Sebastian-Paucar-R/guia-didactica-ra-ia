"""Recuperación léxica para la búsqueda híbrida (ver `RAGService.recuperar`).

Por qué existe: con `all-MiniLM-L6-v2` (entrenado en inglés) sobre los documentos en español, la similitud de
embeddings no distingue bien entre normas parecidas. Para "¿Qué es ISO/IEC 25010?" los 4 fragmentos más cercanos
eran de 29110, 9001 (x2) y 27002 (0,71-0,72), aunque el documento de la 25010 empieza con su definición
(reportes/comparativa_modelos.md; medida completa en reportes/calidad_recuperacion.md). Un número de norma es
justo lo que un embedding generaliza y una búsqueda léxica no: "25010" solo aparece en ese documento.

Dos señales léxicas, que se fusionan con la densa por Reciprocal Rank Fusion en `RAGService.recuperar`:
  - Identificador de norma (activa por defecto): si la consulta nombra el número de una norma (25010, 9001...) y
    hay un documento cuyo título lo lleva, los fragmentos de ese documento entran en una lista propia (ordenados
    por similitud densa). Una consulta sin números, o con el número de una norma sin documento propio (29119),
    no genera esta lista y se queda con la recuperación densa de siempre.
  - BM25 sobre el texto de cada fragmento con el título de su documento delante (RECUPERACION_HIBRIDA_BM25,
    apagada). Recupera algo mejor en el banco, pero en la evaluación completa del tutor subió fragmentos que
    solo mencionan un término de pasada; con eso el término cuenta como respaldado y el tutor dejó de decir "no
    está en los documentos" (inventó los roles de Scrum). Detalle en reportes/calidad_recuperacion.md.

Sin dependencias nuevas (BM25 es ~20 líneas) y todo en memoria: con ~125 fragmentos se reconstruye en
milisegundos, y `RAGService` lo descarta cada vez que el índice cambia.
"""
import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass

# Palabras vacías del español (y de las preguntas típicas) que no deben pesar en BM25: con pocos fragmentos su
# idf no es despreciable y "qué es la" empujaría fragmentos que no tienen nada que ver.
_VACIAS = frozenset("""
a al algo como con cual cuales cuando de del donde e el ella en entre es esa ese eso esta este esto la las le
lo los me mi mas muy no o para pero por que quien se segun ser si sin sobre su sus te tiene tu un una uno unos
y ya cuanto cuanta cuantos cuantas hay son esta estan qué cuál cómo puedo debe deben sirve trata establece
explica explicame dime norma normas
""".split())

# Número de norma: 4-5 dígitos (9001, 12207, 25010). Los años (2015, 2023) también tienen 4 dígitos, pero solo
# cuentan si coinciden con el identificador de un documento indexado, y ningún título lleva un año.
_NUMERO_NORMA = re.compile(r"(?<![\d.])\d{4,5}(?![\d.])")


def tokenizar(texto: str) -> list[str]:
    """Minúsculas, sin tildes, solo alfanuméricos, sin palabras vacías."""
    texto = unicodedata.normalize("NFKD", texto.lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return [t for t in re.findall(r"[a-z0-9]+", texto) if t not in _VACIAS]


def numeros_de_norma(texto: str) -> set[str]:
    return set(_NUMERO_NORMA.findall(texto))


class BM25:
    """Okapi BM25 clásico (k1=1.5, b=0.75) sobre una lista fija de textos."""

    def __init__(self, textos: list[str], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self._tf = [Counter(tokenizar(t)) for t in textos]
        self._largo = [sum(c.values()) for c in self._tf]
        self._largo_medio = (sum(self._largo) / len(self._largo)) if self._largo else 0.0
        n = len(textos)
        df = Counter(t for c in self._tf for t in c)
        self._idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def puntajes(self, consulta: str) -> list[float]:
        terminos = [t for t in tokenizar(consulta) if t in self._idf]
        salida = []
        for tf, largo in zip(self._tf, self._largo):
            s = 0.0
            for t in terminos:
                f = tf.get(t, 0)
                if f:
                    s += self._idf[t] * f * (self.k1 + 1) / (
                        f + self.k1 * (1 - self.b + self.b * largo / (self._largo_medio or 1)))
            salida.append(s)
        return salida


@dataclass(frozen=True)
class Fragmento:
    id: str
    texto: str
    metadata: dict
    titulo: str


class IndiceLexico:
    """Las dos listas léxicas sobre los fragmentos del índice vectorial (mismos ids que en Chroma)."""

    def __init__(self, fragmentos: list[Fragmento]):
        self.fragmentos = fragmentos
        self._bm25 = BM25([f"{f.titulo} {f.texto}" for f in fragmentos])
        # Números de norma del título de cada documento ("ISO/IEC 25010 — Modelo de..." -> {"25010"})
        self._numeros = [numeros_de_norma(f.titulo) for f in fragmentos]

    def _permitido(self, i: int, archivos: set[str] | None) -> bool:
        return archivos is None or self.fragmentos[i].metadata.get("nombre_archivo") in archivos

    def bm25(self, consulta: str, n: int, archivos: set[str] | None = None) -> list[int]:
        """Posiciones de los n fragmentos con mayor BM25 (> 0), mayor primero."""
        puntajes = self._bm25.puntajes(consulta)
        orden = sorted((i for i, s in enumerate(puntajes) if s > 0 and self._permitido(i, archivos)),
                       key=lambda i: -puntajes[i])
        return orden[:n]

    def por_identificador(self, consulta: str, archivos: set[str] | None = None) -> list[int]:
        """Posiciones de los fragmentos de documentos cuyo título lleva un número de norma nombrado en la consulta
        (sin orden propio: `RAGService.recuperar` los ordena por similitud densa). Vacío si no nombra ninguno."""
        nombrados = numeros_de_norma(consulta)
        if not nombrados:
            return []
        return [i for i, nums in enumerate(self._numeros) if nums & nombrados and self._permitido(i, archivos)]


def fusion_rrf(listas: list[list[str]], k: int = 60) -> list[str]:
    """Reciprocal Rank Fusion: cada lista aporta 1/(k + posición) a cada id; mayor suma primero. k=60 es el valor
    estándar (Cormack et al., 2009): atenúa la diferencia entre los primeros puestos para que ninguna señal sola
    domine. A igual puntaje gana el orden de la primera lista (la densa), por estabilidad."""
    puntaje: dict[str, float] = {}
    for lista in listas:
        for pos, id_ in enumerate(lista):
            puntaje[id_] = puntaje.get(id_, 0.0) + 1.0 / (k + pos + 1)
    return sorted(puntaje, key=lambda i: -puntaje[i])

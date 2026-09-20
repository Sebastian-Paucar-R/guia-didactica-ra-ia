"""Temario de la asignatura Normativas de Ingeniería de Software, cargado de configuracion/silabo.yaml.

El YAML es la única fuente del temario: el filtro de pertinencia clasifica contra él, las redirecciones
proponen temas tomados de él y la auditoría de cobertura lo cruza con los documentos indexados. Aquí solo
hay lectura, validación, búsqueda por palabras clave y los textos que se insertan en los prompts.

El temario cubre más que los documentos indexados (p. ej. Scrum o DORA no tienen fuente en documentacion/):
una pregunta sobre ellos es del ámbito aunque el RAG no tenga contexto.
"""
import re
import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml

from app.core.config import settings


def normalizar(texto: str) -> str:
    """Minúsculas, sin acentos ni signos, espacios simples: base de toda comparación con el temario."""
    sin_acentos = "".join(
        c for c in unicodedata.normalize("NFKD", texto.lower()) if not unicodedata.combining(c)
    )
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", sin_acentos)).strip()


@dataclass(frozen=True)
class Tema:
    id: str
    nombre: str
    unidad: int
    unidad_titulo: str
    palabras_clave: tuple[str, ...]
    archivos: tuple[str, ...]
    complementario: bool = False
    _patrones: tuple = field(default=(), repr=False, compare=False)   # (palabra_clave, regex, peso, débil)

    def etiqueta(self) -> str:
        return f"Unidad {self.unidad}: {self.nombre}"


@dataclass(frozen=True)
class Coincidencia:
    """Resultado de buscar un texto en el temario por palabras clave."""
    tema: Tema
    palabras: tuple[str, ...]   # palabras clave del tema que aparecen en el texto
    puntaje: int


def _compilar(palabra_clave: str):
    """(regex, peso) de una palabra clave. Un `*` al final de una palabra admite cualquier terminación.
    Los números de norma pesan 3 (lo más específico); el resto, tantos puntos como palabras."""
    piezas = []
    for palabra in palabra_clave.split():
        comodin = palabra.endswith("*")
        partes = normalizar(palabra.rstrip("*")).split()
        if not partes:
            continue
        piezas.extend(re.escape(p) for p in partes)
        if comodin:
            piezas[-1] += "[a-z0-9]*"
    if not piezas:
        raise ValueError(f"palabra clave vacía: {palabra_clave!r}")
    regex = re.compile(r"(?<![a-z0-9])" + r" ".join(piezas) + r"(?![a-z0-9])")
    return regex, 3 if len(piezas) == 1 and piezas[0].isdigit() else len(piezas)


@lru_cache(maxsize=4)
def _cargar(ruta: str) -> tuple[dict, tuple[Tema, ...]]:
    archivo = Path(ruta)
    if not archivo.is_file():
        raise FileNotFoundError(f"No se encontró el sílabo en {archivo} (variable SILABO_PATH)")
    datos = yaml.safe_load(archivo.read_text(encoding="utf-8")) or {}
    titulos = {u["numero"]: u["titulo"] for u in datos.get("unidades", [])}
    if not titulos or not datos.get("temas"):
        raise ValueError(f"{archivo}: faltan 'unidades' o 'temas'")
    temas: list[Tema] = []
    for t in datos["temas"]:
        for campo in ("id", "nombre", "unidad", "palabras_clave"):
            if not t.get(campo):
                raise ValueError(f"{archivo}: un tema no tiene '{campo}': {t}")
        if t["unidad"] not in titulos:
            raise ValueError(f"{archivo}: el tema {t['id']} apunta a la unidad inexistente {t['unidad']}")
        crudas = [str(k) for k in t["palabras_clave"]]
        claves = tuple(k.lstrip("~").strip() for k in crudas)
        temas.append(Tema(
            id=str(t["id"]), nombre=str(t["nombre"]), unidad=int(t["unidad"]), unidad_titulo=titulos[t["unidad"]],
            palabras_clave=claves, archivos=tuple(t.get("archivos") or ()),
            complementario=bool(t.get("complementario", False)),
            _patrones=tuple((k, *_compilar(k), cruda.startswith("~")) for k, cruda in zip(claves, crudas)),
        ))
    ids = [t.id for t in temas]
    if len(set(ids)) != len(ids):
        raise ValueError(f"{archivo}: ids de tema repetidos: {sorted({i for i in ids if ids.count(i) > 1})}")
    temas.sort(key=lambda t: (t.unidad, [int(p) if p.isdigit() else p for p in t.id.split(".")]))
    return datos, tuple(temas)


def cargar_silabo(ruta: Path | str | None = None) -> dict:
    """El YAML tal cual (asignatura, unidades, temas). Falla al arrancar si el archivo es inválido."""
    return _cargar(str(ruta or settings.SILABO_PATH))[0]


def temas(ruta: Path | str | None = None) -> list[Tema]:
    return list(_cargar(str(ruta or settings.SILABO_PATH))[1])


def unidades() -> list[dict]:
    """[{numero, titulo, temas: [Tema]}] en orden."""
    todos = temas()
    return [
        {"numero": u["numero"], "titulo": u["titulo"], "temas": [t for t in todos if t.unidad == u["numero"]]}
        for u in sorted(cargar_silabo()["unidades"], key=lambda u: u["numero"])
    ]


def temas_planos() -> list[str]:
    """Todos los temas como líneas 'Unidad N: tema' (índice = posición en `temas()`)."""
    return [t.etiqueta() for t in temas()]


def texto_temas_numerados() -> str:
    return "\n".join(f"{i}. {t}" for i, t in enumerate(temas_planos(), start=1))


def texto_silabo(con_temas: bool = True) -> str:
    """Temario en texto plano, para incluir en los prompts."""
    lineas = []
    for u in unidades():
        lineas.append(f"Unidad {u['numero']}: {u['titulo']}")
        if con_temas:
            lineas.extend(f"  - {t.nombre}" for t in u["temas"])
    return "\n".join(lineas)


def texto_clasificador(max_claves: int = 6) -> str:
    """Temas numerados con unidad y algunas palabras clave: lo que el clasificador LLM usa para decidir.
    Se muestran las palabras completas (sin comodín): una raíz como "metodolog" solo confunde al modelo."""
    lineas = []
    for i, t in enumerate(temas(), start=1):
        completas = [k for k in t.palabras_clave if "*" not in k] or [k.replace("*", "") for k in t.palabras_clave]
        claves = ", ".join(completas[:max_claves])
        lineas.append(f"{i}. [Unidad {t.unidad}] {t.nombre} (palabras clave: {claves})")
    return "\n".join(lineas)


def texto_para_embedding(tema: Tema) -> str:
    """Texto que representa al tema al compararlo por similitud semántica con una pregunta."""
    return f"{tema.nombre}. " + ", ".join(k.replace("*", "") for k in tema.palabras_clave)


def buscar_por_palabras_clave(texto: str) -> Coincidencia | None:
    """Tema del sílabo cuyas palabras clave aparecen en `texto`; None si ninguno.

    Cada palabra clave fuerte que aparece suma su peso (una frase pesa más que un término suelto, un número de
    norma más que ambos). Gana el tema de mayor puntaje; en empate, el de la coincidencia más pesada y luego el
    primero. Las palabras débiles (`~` en el YAML) solo deciden si no apareció ninguna fuerte."""
    n = normalizar(texto)
    if not n:
        return None
    for debiles in (False, True):
        mejor: tuple[tuple[int, int], Coincidencia] | None = None
        for t in temas():
            halladas = [(k, peso) for k, regex, peso, debil in t._patrones if debil == debiles and regex.search(n)]
            if not halladas:
                continue
            puntaje = sum(peso for _, peso in halladas)
            clave = (puntaje, max(peso for _, peso in halladas))
            if mejor is None or clave > mejor[0]:
                mejor = (clave, Coincidencia(t, tuple(k for k, _ in halladas), puntaje))
        if mejor:
            return mejor[1]
    return None


def ubicar_en_silabo(termino: str) -> list[str]:
    """Dónde trata el sílabo un término (p. ej. 'Scrum' -> Unidad 1, 'ISO/IEC/IEEE 29119' -> Unidad 4).
    Busca en el nombre y en las palabras clave de cada tema. Devuelve líneas 'Unidad N (título): tema'; es la
    ubicación real, para no depender de que el LLM adivine la unidad correcta."""
    buscado = normalizar(termino)
    if not buscado:
        return []
    patron = re.compile(r"(?<![a-z0-9])" + re.escape(buscado) + r"(?![a-z0-9])")
    return [
        f"Unidad {t.unidad} ({t.unidad_titulo}): {t.nombre}"
        for t in temas()
        if patron.search(normalizar(t.nombre)) or any(patron.search(normalizar(k)) for k in t.palabras_clave)
    ]

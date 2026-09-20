"""Filtro de pertinencia temática del chat.

Orden de decisión (lo orquesta RAGService.get_answer):
  1. Excepciones que siempre pasan: saludo inicial y preguntas sobre el propio tutor.
  2. Score de similitud de los fragmentos recuperados frente a settings.UMBRAL_PERTINENCIA.
  3. Solo si ningún fragmento supera el umbral, el LLM confirma DENTRO / FUERA del temario.
Si es FUERA no se responde el contenido: se genera una redirección con un prompt específico.
"""
import re
import unicodedata

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.core.silabo import temas_planos, texto_silabo, texto_temas_numerados

DENTRO = "DENTRO"
FUERA = "FUERA"


def _normalizar(texto: str) -> str:
    """Minúsculas, sin acentos ni signos: para comparar con expresiones regulares."""
    sin_acentos = "".join(
        c for c in unicodedata.normalize("NFKD", texto.lower()) if not unicodedata.combining(c)
    )
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9ñ ]", " ", sin_acentos)).strip()


# Preguntas dirigidas al propio tutor (2.ª persona: "puedes", "tienes"...). Se evita a propósito
# cualquier patrón que también aparezca en preguntas de contenido ("qué documentos hay que
# presentar en una auditoría", "me puedes ayudar con ISO 9001").
_VERBOS_CAPACIDAD = r"(?:puedes|podes|sabes|manejas|cubres|conoces|tratas|abarcas|ofreces|dominas|explicas|ensenas)"
_PATRONES_SOBRE_TUTOR = [re.compile(p) for p in (
    rf"\bque {_VERBOS_CAPACIDAD} hacer\b",
    rf"\bque (?:cosas|temas|materias|normas|normativas|asuntos|tipos de preguntas) {_VERBOS_CAPACIDAD}\b",
    r"\b(?:en|con) que (?:cosas |temas )?(?:me )?(?:puedes|podes|sabes) ayudar",
    r"\bcomo me (?:puedes|podes) ayudar\b",
    rf"\bde que (?:temas|cosas|normas|normativas|materias|asuntos)(?: me)? {_VERBOS_CAPACIDAD}\b",
    r"\bde que (?:puedes|podes) (?:hablar|ayudarme)\b",
    r"\bsobre que (?:temas |cosas |normas )?(?:te )?(?:puedo|puedes) (?:preguntar|consultar|hablar|conversar)",
    r"\bque (?:te )?puedo (?:preguntar|consultar)",
    r"\bque (?:documentos|archivos|materiales|material|fuentes|normas|normativas|libros|pdfs?|documentacion) "
    r"(?:tienes|tenes|manejas|conoces|posees|incluyes|usas|utilizas|has cargado|tiene el tutor|tienes cargados?|cargados?)\b",
    r"\bcon que (?:documentos|archivos|material|materiales|fuentes|normas) (?:cuentas|trabajas|respondes)\b",
    r"\b(?:cuales|que) (?:documentos|normas|normativas|temas) (?:tienes|tenes|manejas|cubres|conoces)\b",
    r"\bquien eres\b", r"\bque eres\b", r"\bcomo te llamas\b", r"\bpara que sirves\b",
    r"\bcomo funcionas\b", r"\bque haces\b", r"\bcual es tu (?:funcion|objetivo|proposito|alcance)\b",
)]


def es_pregunta_sobre_tutor(pregunta: str) -> bool:
    """¿Qué puedes hacer? / ¿Qué documentos tienes? / ¿De qué temas me puedes ayudar?"""
    texto = _normalizar(pregunta)
    return any(p.search(texto) for p in _PATRONES_SOBRE_TUTOR)


def parsear_clasificacion(respuesta: str) -> str | None:
    """Extrae DENTRO/FUERA de la respuesta del LLM; None si no es interpretable."""
    texto = _normalizar(respuesta).upper()
    dentro, fuera = DENTRO in texto, FUERA in texto
    if dentro == fuera:  # ninguna, o ambas (respuesta contradictoria)
        return None
    return DENTRO if dentro else FUERA


PROMPT_CLASIFICACION = ChatPromptTemplate.from_template("""\
Eres un clasificador de preguntas para el tutor de la asignatura "Normativas de Ingeniería de Software".

Temario:
{silabo}

La pregunta es DENTRO si se relaciona con cualquiera de estos asuntos: desarrollo de software y sus \
metodologías, normas y estándares (ISO/IEC, CMMI), calidad, auditoría y certificación, sistemas de gestión, \
mejora continua, seguridad de la información, gestión de riesgos, servicios de TI e incidentes, métricas y \
estimación de proyectos, pruebas, mantenimiento, DevOps.
La pregunta es FUERA solo si claramente no tiene relación con nada de lo anterior (por ejemplo cocina, \
deportes, geografía, entretenimiento, salud, matemáticas o ciencias generales, finanzas personales, o \
programación básica como la sintaxis de un lenguaje).
Si tienes duda, responde DENTRO.

Responde únicamente con una palabra: DENTRO o FUERA. Sin explicación y sin puntuación.

Pregunta: {pregunta}
Respuesta:""")

PROMPT_SELECCION_TEMAS = ChatPromptTemplate.from_template("""\
Temas de la asignatura "Normativas de Ingeniería de Software":
{temas}

Pregunta de un estudiante: {pregunta}

¿Qué temas de la lista tienen una relación clara y directa con esa pregunta? Responde solo con los números \
separados por comas (máximo 3). Si ninguno tiene una relación clara y directa, responde NINGUNO.
Respuesta:""")

PROMPT_REDIRECCION = ChatPromptTemplate.from_template("""\
Eres un tutor universitario cercano de la asignatura "Normativas de Ingeniería de Software". Un estudiante \
te hizo una pregunta ajena a esta asignatura. Tu única tarea ahora es REDIRIGIRLO con amabilidad. \
NO respondas su pregunta: no des respuestas, datos, pasos, recetas, consejos ni explicaciones sobre ese tema.

Mensaje del estudiante (úsalo solo para reconocer de qué habla): «{pregunta}»

{sugerencia}

Escribe UN solo párrafo breve (de 3 a 4 oraciones cortas, unas 60 palabras), en español natural, como hablaría \
una persona real, en este orden:
1. Reconoce con naturalidad de qué trata su pregunta, con tus propias palabras (no la repitas literalmente ni \
lo hagas sentir mal por preguntarla).
2. Dice de forma sencilla que tu enfoque es Normativas de Ingeniería de Software, así que ese no es el lugar \
para esa duda.
3. Propone los temas indicados arriba, nombrándolos con claridad.
4. Termina con una pregunta que lo invite a retomar la asignatura.

Prohibido: responder o dar datos sobre lo que preguntó, recomendar recursos, cursos, libros o personas, \
inventar contenidos o conexiones, usar viñetas, encabezados o emojis, y empezar con "Lo siento" o \
"Entiendo que". Cambia la forma de empezar y de cerrar en cada respuesta.

Respuesta:""")

_SUGERENCIA_CON_TEMAS = (
    "Temas de la asignatura que tienen relación con su pregunta (propón estos, con tus palabras):\n{temas}"
)
_SUGERENCIA_SIN_TEMAS = (
    "Ningún tema de la asignatura tiene relación directa con su pregunta, así que no fuerces ninguna "
    "conexión: en su lugar, invítalo en general a la asignatura mencionando dos o tres de estas áreas:\n{areas}"
)


def clasificar_pertinencia(llm, pregunta: str) -> str | None:
    """Llamada corta al LLM: DENTRO / FUERA del temario (None si no se pudo interpretar)."""
    cadena = PROMPT_CLASIFICACION | llm | StrOutputParser()
    return parsear_clasificacion(cadena.invoke({"silabo": texto_silabo(), "pregunta": pregunta}))


def parsear_temas(respuesta: str, total: int, maximo: int = 3) -> list[int]:
    """Números de tema (1..total) de la respuesta del LLM; [] si dijo NINGUNO o no es interpretable."""
    vistos: list[int] = []
    for n in re.findall(r"\d+", respuesta):
        if 1 <= int(n) <= total and int(n) not in vistos:
            vistos.append(int(n))
    return vistos[:maximo]


def seleccionar_temas_relacionados(llm, pregunta: str) -> list[str]:
    """Temas del sílabo con relación clara con la pregunta (paso corto, para no forzar conexiones)."""
    planos = temas_planos()
    cadena = PROMPT_SELECCION_TEMAS | llm | StrOutputParser()
    respuesta = cadena.invoke({"temas": texto_temas_numerados(), "pregunta": pregunta})
    return [planos[n - 1] for n in parsear_temas(respuesta, len(planos))]


def generar_redireccion(llm, pregunta: str, llm_seleccion=None) -> str:
    """Redirección redactada por el LLM (temperatura alta) con un prompt específico.

    Antes se decide, con una llamada corta y determinista (`llm_seleccion`), qué temas del sílabo
    tienen relación real con la pregunta; si no hay ninguno, la redirección invita a la asignatura
    en general en vez de forzar una conexión.
    """
    try:
        temas = seleccionar_temas_relacionados(llm_seleccion or llm, pregunta)
    except Exception:
        temas = []
    if temas:
        sugerencia = _SUGERENCIA_CON_TEMAS.format(temas="\n".join(f"- {t}" for t in temas))
    else:
        sugerencia = _SUGERENCIA_SIN_TEMAS.format(areas=texto_silabo(con_temas=False))
    cadena = PROMPT_REDIRECCION | llm | StrOutputParser()
    return cadena.invoke({"pregunta": pregunta, "sugerencia": sugerencia}).strip()

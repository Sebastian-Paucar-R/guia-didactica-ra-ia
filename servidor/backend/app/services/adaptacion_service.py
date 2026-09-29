"""Adaptación del tutor al estudiante: señales observables, actualización gradual del perfil y directiva del prompt.

Dos mitades que no se mezclan:

1. `aplicar_turno` (después de responder) mira lo que el estudiante HIZO en el mensaje (pidió aclarar, pidió
   ejemplos, respondió bien una pregunta de reflexión), nunca lo que dice de sí mismo, y mueve el perfil en pasos
   pequeños. Ningún mensaje cambia un nivel más de 0,4 ni una preferencia más de un escalón.
2. `construir_adaptacion` (antes de responder) convierte el perfil en una directiva para el prompt y en un
   `segmento` para el caché. La directiva solo habla de CÓMO explicar (profundidad, andamiaje, referencias a lo ya
   visto); jamás aporta datos: el contenido sigue saliendo solo del CONTEXTO recuperado y las verificaciones de la
   salida (normas sin respaldo, términos sin respaldo, pasos de una tarea) se aplican igual a lo adaptado.

Invariante del caché: `segmento` es función de lo que la directiva realmente dice, así que dos estudiantes comparten
una respuesta guardada si y solo si su prompt lleva el mismo ajuste. El perfil neutro (estudiante nuevo o anónimo)
produce texto y segmento vacíos: el prompt es idéntico al de antes de existir el perfil.

La profundidad que devuelve `construir_adaptacion` es la preferida del perfil (o "media" en una TAREA); quien la
acota además por lo que de verdad se recuperó (poco contexto -> nunca "extensa", nunca PROFUNDIZAR sin límite) es
`rag_service`, con `tutor.nivel_de_contexto`, porque `construir_adaptacion` se llama antes de recuperar (en el
caché) y no siempre conoce el contexto. Cuando lo acota, recalcula el segmento con `segmento_de` (no con la
profundidad preferida): el caché debe guardar bajo el ajuste que de verdad generó la respuesta, aunque eso le
cueste algún acierto de caché a quien prefiere "extensa" y pregunta algo con poco material (documentado, no un
error: nunca sirve contenido con la extensión equivocada, solo dejará de reutilizar esa entrada).
"""
import re
from collections import Counter
from dataclasses import dataclass

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.models.perfil import (
    PROFUNDIDADES, VENTANA_SENALES, CambioNivel, PerfilEstudiante, TemaReciente)
from app.services import tutor_service as tutor
from app.services.memoria_service import Turno
from app.services.pertinencia_service import _normalizar

# ---------------------------------------------------------------------------
# Parámetros de gradualidad
# ---------------------------------------------------------------------------

PASO_CONFUSION = 0.4        # lo que baja el nivel de la unidad cada vez que pide aclarar o dice que no entendió
PASO_REFLEXION = 0.3        # lo que sube al responder bien una pregunta de reflexión
UMBRAL_RECURRENCIA = 3      # señales de un mismo tipo, en la ventana reciente, para cambiar profundidad o estilo
ACLARACIONES_PARA_DIFICULTAD = 2
MAX_REFERENCIAS = 2
MIN_PALABRAS_REFLEXION = 8

# ---------------------------------------------------------------------------
# Señales observables (sobre el mensaje normalizado: minúsculas, sin acentos ni signos)
# ---------------------------------------------------------------------------


def _compilar(*patrones: str) -> list[re.Pattern]:
    return [re.compile(p) for p in patrones]


# Dice que no entendió: baja el nivel y marca el tema como dificultad enseguida
_NO_ENTENDI = _compilar(
    r"\bno (?:lo |la |te )?(?:entendi|entiendo|comprendi|comprendo)\b",
    r"\bno me (?:quedo|queda) claro\b", r"\bsigo sin (?:entender|comprender)\b",
)
# Pide que se lo vuelvan a explicar: baja el nivel; es dificultad a partir de la segunda vez en el mismo tema
_ACLARACION = _compilar(
    r"\bexplic\w* (?:eso |esto |lo )?(?:mejor|de nuevo|otra vez)\b", r"\botra vez\b", r"\bde nuevo\b",
    r"\brep(?:ite|etir)\w*", r"\baclar\w*",
)
_EJEMPLO = _compilar(
    r"\b(?:dame|damelo|dime|pon|ponme|muestrame|quiero|necesito|ilustra\w*|ejemplific\w*)\b.{0,20}\bejemplos?\b",
    r"\bcon (?:un |algun )?ejemplos?\b", r"\b(?:un|otro|mas) ejemplos?\b", r"\bejemplos? (?:practic\w*|real\w*|concret\w*)\b",
)
_AMPLIAR = _compilar(
    r"\bampli(?:a|ar|ame|alo|ala|acion)\b", r"\bprofundiz\w+", r"\bmas detalles?\b", r"\bdetalla(?:me|lo)?\b", r"\bdesarrolla(?:me|lo|la)?\b",
    r"\bexplic\w* (?:me )?mas\b",
)
_CORTAR = _compilar(
    r"\bmas (?:corto|breve|resumid\w*)\b", r"\bresum(?:e|elo|eme|ela)\b", r"\ben resumen\b", r"\bbrevemente\b",
    r"\ben pocas palabras\b", r"\bal grano\b", r"\bmuy (?:largo|extenso)\b", r"\bdemasiado (?:largo|extenso|texto|detalle)\b",
    r"\bsin tanto detalle\b",
)
_COMPARAR = _compilar(
    r"\bdiferencias? entre\b", r"\bcompar(?:a|ar|ame|alo|ala|acion|ando)\b", r"\bvs\b", r"\bversus\b",
    r"\bse diferencia\w*", r"\bcontrasta\w*",
)

_ETIQUETAS = (("no_entendi", _NO_ENTENDI), ("aclaracion", _ACLARACION), ("ejemplo", _EJEMPLO),
              ("ampliar", _AMPLIAR), ("cortar", _CORTAR), ("comparar", _COMPARAR))
# De estas señales se infieren profundidad y estilo (la confusión mueve el nivel, no las preferencias)
_SENALES_DE_PREFERENCIA = ("ejemplo", "ampliar", "cortar", "comparar")


def detectar_senales(mensaje: str) -> set[str]:
    """Etiquetas de lo que el mensaje hace: no_entendi | aclaracion | ejemplo | ampliar | cortar | comparar."""
    texto = _normalizar(mensaje)
    return {etiqueta for etiqueta, patrones in _ETIQUETAS if any(p.search(texto) for p in patrones)}


# ---------------------------------------------------------------------------
# Reflexión respondida correctamente
# ---------------------------------------------------------------------------

_POCO_INFORMATIVAS = {"porque", "cuando", "entonces", "tambien", "donde", "sobre", "desde", "hasta", "puede", "pueden",
                      "cual", "cuales", "siempre", "ademas", "todos", "todas", "cada", "estos", "estas", "hacer",
                      "tiene", "tienen", "seria", "serian", "podria", "podrian", "usaria", "usar", "deberia"}


def _terminos(texto: str) -> set[str]:
    return {p for p in _normalizar(texto).split() if len(p) >= 5 and p not in _POCO_INFORMATIVAS}


# Lo único que puede sobrar en un seguimiento sin tema propio ("no entendí, mejor explícame eso, por favor"): palabras
# funcionales y de cortesía. Cualquier otra palabra (aunque sea corta: "gol") puede ser un tema.
_DE_SEGUIMIENTO = {
    "el", "la", "lo", "los", "las", "un", "una", "de", "del", "que", "por", "me", "te", "se", "y", "o", "a", "en", "es", "no", "si",
    "eso", "esto", "esa", "ese", "mas", "muy", "bien", "ya", "con", "para", "como", "otra", "vez", "otro", "mejor", "favor",
    "gracias", "claro", "duda", "dudas", "puedes", "podrias", "porfa", "sigo", "explicame", "explicamelo", "explica",
    "entendi", "entender", "entiendo", "ejemplo", "ejemplos", "algo", "nada", "poco", "mi", "tu", "sin", "sobre"}


def es_seguimiento_puro(mensaje: str) -> bool:
    """¿El mensaje solo pide aclarar, ampliar o ilustrar lo anterior, sin nombrar un tema propio? Quitadas las frases de
    señal, solo quedan palabras funcionales o de cortesía ("explícame otra vez la relatividad" deja «relatividad»)."""
    texto = _normalizar(mensaje)
    for _, patrones in _ETIQUETAS:
        for p in patrones:
            texto = p.sub(" ", texto)
    return set(texto.split()) <= _DE_SEGUIMIENTO


def es_candidata_reflexion(mensaje: str, turnos: list[Turno]) -> bool:
    """¿Parece el mensaje una respuesta a la pregunta de reflexión con la que cerró el tutor? Filtro barato y sin LLM
    que evita juzgar todos los mensajes: el turno anterior fue una respuesta que termina en pregunta y el mensaje es
    una afirmación (no una pregunta ni un pedido), con cierta extensión y que habla de lo mismo que el tutor."""
    if not turnos:
        return False
    previo = turnos[-1]
    if previo.tipo != "respuesta" or not previo.respuesta.rstrip().endswith("?"):
        return False
    if "?" in mensaje or len(_normalizar(mensaje).split()) < MIN_PALABRAS_REFLEXION:
        return False
    if detectar_senales(mensaje) & {"no_entendi", "aclaracion", "ejemplo", "ampliar", "cortar", "comparar"}:
        return False
    if tutor.detectar_intencion_por_senales(mensaje) == tutor.TAREA:
        return False
    return len(_terminos(mensaje) & _terminos(previo.respuesta)) >= 2


PROMPT_JUICIO = ChatPromptTemplate.from_template("""\
Un tutor universitario cerró su explicación con una pregunta de reflexión y el estudiante respondió. Evalúa la \
respuesta del estudiante SOLO frente a lo que explicó el tutor.

Explicación y pregunta del tutor:
{tutor}

Respuesta del estudiante:
{estudiante}

Clasifica:
- CORRECTA: contesta la pregunta y es coherente con la explicación.
- INCOMPLETA: es parcial, vaga o solo repite lo que dijo el tutor.
- INCORRECTA: contradice la explicación o no contesta la pregunta.
Ante la duda, INCOMPLETA. Responde únicamente con una palabra.

Veredicto:""")

_VEREDICTO = re.compile(r"\b(CORRECTA|INCORRECTA|INCOMPLETA)\b")


def parsear_juicio(respuesta: str) -> str | None:
    """CORRECTA | INCOMPLETA | INCORRECTA; None si no hay un veredicto claro (más de uno distinto o ninguno)."""
    encontrados = set(_VEREDICTO.findall(_normalizar(respuesta).upper()))
    return encontrados.pop() if len(encontrados) == 1 else None


def respondio_bien(llm, turnos: list[Turno], mensaje: str) -> bool:
    """El juez (LLM corto y determinista) confirma que el mensaje responde bien la reflexión del turno anterior. Es
    deliberadamente conservador: si el LLM falla o no da un veredicto claro, no cuenta."""
    if not es_candidata_reflexion(mensaje, turnos):
        return False
    try:
        veredicto = (PROMPT_JUICIO | llm | StrOutputParser()).invoke(
            {"tutor": turnos[-1].respuesta, "estudiante": mensaje})
    except Exception:
        return False
    return parsear_juicio(veredicto) == "CORRECTA"


# ---------------------------------------------------------------------------
# Actualización del perfil
# ---------------------------------------------------------------------------


def _ubic(ubicacion) -> dict | None:
    """La ubicación llega como dict {unidad, tema_id, tema, metodo} (respuesta del RAG) o como Ubicacion."""
    if ubicacion is None:
        return None
    return ubicacion if isinstance(ubicacion, dict) else ubicacion.como_dict()


def _consumir(senales: list[str], etiqueta: str, cantidad: int) -> None:
    """Quita de la ventana `cantidad` señales de ese tipo (las más antiguas): ya se usaron para cambiar una
    preferencia, así que el siguiente escalón exige evidencia nueva."""
    for _ in range(cantidad):
        senales.remove(etiqueta)


def _inferir_preferencias(perfil: PerfilEstudiante) -> None:
    cuenta = Counter(perfil.senales_recientes)
    # Profundidad: un solo escalón por vez (nunca de breve a extensa de golpe)
    quiere_mas, quiere_menos = cuenta["ampliar"] >= UMBRAL_RECURRENCIA, cuenta["cortar"] >= UMBRAL_RECURRENCIA
    if quiere_mas != quiere_menos:
        posicion = PROFUNDIDADES.index(perfil.profundidad_preferida)
        nueva = min(max(posicion + (1 if quiere_mas else -1), 0), len(PROFUNDIDADES) - 1)
        if nueva != posicion:
            perfil.profundidad_preferida = PROFUNDIDADES[nueva]
            _consumir(perfil.senales_recientes, "ampliar" if quiere_mas else "cortar", UMBRAL_RECURRENCIA)
    # Estilo: gana el que se pide de forma recurrente y más que el actual; un empate no decide nada
    candidatos = {"ejemplos": cuenta["ejemplo"], "comparativo": cuenta["comparar"]}
    actual = candidatos.get(perfil.estilo_preferido, 0)
    validos = sorted(((n, e) for e, n in candidatos.items() if n >= UMBRAL_RECURRENCIA and n > actual), reverse=True)
    if validos and (len(validos) == 1 or validos[0][0] > validos[1][0]):
        _, estilo = validos[0]
        perfil.estilo_preferido = estilo
        _consumir(perfil.senales_recientes, "ejemplo" if estilo == "ejemplos" else "comparar", UMBRAL_RECURRENCIA)


def ultimo_tema(perfil: PerfilEstudiante) -> TemaReciente | None:
    return perfil.historial_resumido[-1] if perfil.historial_resumido else None


def aplicar_turno(perfil: PerfilEstudiante, mensaje: str, ubicacion, reflexion_correcta: bool = False,
                  fecha: str | None = None, seguimiento: bool = False) -> list[CambioNivel]:
    """Actualiza el perfil con lo observable de un turno y devuelve los cambios de nivel (para el progreso).

    - Pide aclarar / dice que no entendió: baja `PASO_CONFUSION` el nivel de la unidad; el tema pasa a
      `temas_con_dificultad` si lo dijo explícitamente o si ya es la segunda aclaración sobre él.
    - Respondió bien una reflexión: sube `PASO_REFLEXION` el nivel de la unidad del turno anterior y, si ese tema
      era una dificultad, deja de serlo.
    - Pide ejemplos / ampliar / resumir / comparar de forma recurrente: cambia estilo o profundidad (un escalón).
    Un seguimiento ("explícame eso mejor", "dame otro ejemplo") sigue en el tema anterior: solo se toma la ubicación del
    mensaje si nombra un tema con palabras clave del sílabo. Si el filtro lo ubicó por embedding o con el LLM
    (`metodo` distinto) esa ubicación es una conjetura sobre un mensaje sin tema propio, y una conjetura errónea
    ensuciaría el historial y cambiaría el nivel de otra unidad; entonces se atribuye al último tema visto.
    """
    ub = _ubic(ubicacion)
    if seguimiento and ub and ub.get("metodo") != "palabras_clave":
        ub = None
    previo = ultimo_tema(perfil)          # el tema del turno anterior, antes de anotar el de este
    senales = detectar_senales(mensaje)
    if ub:
        perfil.registrar_tema(ub["tema_id"], ub["tema"], ub["unidad"], fecha)
    cambios: list[CambioNivel] = []

    def mover(unidad: int, delta: float, motivo: str, tema_id: str | None) -> None:
        antes, despues = perfil.mover_nivel(unidad, delta)
        if despues != antes:
            cambios.append(CambioNivel(unidad=unidad, nivel=despues, motivo=motivo, tema_id=tema_id))

    if senales & {"no_entendi", "aclaracion"}:
        objetivo = ub or (previo.model_dump() if previo else None)
        if objetivo:
            mover(objetivo["unidad"], -PASO_CONFUSION, "confusion", objetivo["tema_id"])
            tema_id = objetivo["tema_id"]
            perfil.aclaraciones_por_tema[tema_id] = perfil.aclaraciones_por_tema.get(tema_id, 0) + 1
            if ("no_entendi" in senales or perfil.aclaraciones_por_tema[tema_id] >= ACLARACIONES_PARA_DIFICULTAD) \
                    and tema_id not in perfil.temas_con_dificultad:
                perfil.temas_con_dificultad.append(tema_id)
    elif reflexion_correcta and previo:
        mover(previo.unidad, PASO_REFLEXION, "reflexion_correcta", previo.tema_id)
        if previo.tema_id in perfil.temas_con_dificultad:
            perfil.temas_con_dificultad.remove(previo.tema_id)
        perfil.aclaraciones_por_tema.pop(previo.tema_id, None)

    perfil.senales_recientes.extend(e for e in _SENALES_DE_PREFERENCIA if e in senales)
    del perfil.senales_recientes[:-VENTANA_SENALES]
    _inferir_preferencias(perfil)
    return cambios


# ---------------------------------------------------------------------------
# Directiva para el prompt
# ---------------------------------------------------------------------------

_CABECERA = (
    "\n\nAJUSTE AL ESTUDIANTE (cambia solo CÓMO explicas, nunca QUÉ dice la norma): el contenido, las cifras, los "
    "identificadores y el rigor salen del CONTEXTO exactamente igual que para cualquier otra persona, y tu rol de "
    "tutor y las reglas de arriba siguen intactos. No menciones que estás adaptando la respuesta ni hables de su nivel.")

_ANDAMIAJE = {
    "bajo": (
        "\n- Andamiaje: parte de una analogía cotidiana o de una situación sencilla de un equipo de software y solo "
        "después nombra el concepto técnico; define cada término la primera vez que aparece y usa frases cortas. La "
        "analogía solo ilustra la idea: los datos, niveles, categorías, cifras y normas que menciones salen únicamente "
        "del CONTEXTO, y no inventes detalles para que la analogía encaje."),
    "alto": "\n- Andamiaje: ve directo al concepto con vocabulario técnico, sin analogías básicas.",
}
# La pregunta de cierre no va en una tarea: una tarea termina invitando a hacer el primer paso
_CIERRE = {
    "bajo": " Cierra con una pregunta sencilla que le permita comprobar lo esencial.",
    "alto": (" Cierra con UNA pregunta socrática exigente (un porqué, un «qué pasaría si…» o un contraste) que lo "
             "obligue a razonar y no solo a repetir lo leído."),
}
_DIFICULTAD = (
    "\n- Este tema le ha costado antes: avanza en pasos más pequeños y aclara primero lo que suele confundirse.")
_CIERRE_DIFICULTAD = " Comprueba que quedó claro con una pregunta sencilla."
_ESTILOS = {
    "ejemplos": (
        "\n- Estilo: apóyate en una situación concreta de un proyecto de software (el ejemplo es la situación; los "
        "conceptos, cifras y normas siguen saliendo solo del CONTEXTO)."),
    "comparativo": (
        "\n- Estilo: explica primero lo que el CONTEXTO dice de esta norma y, solo si el CONTEXTO describe otra norma o "
        "enfoque cercano, contrástalo en una frase nombrándolo con su identificador. Cada característica pertenece a la "
        "norma a la que el CONTEXTO se la atribuye: no le traslades a una lo que se dice de la otra. Si el CONTEXTO no "
        "trae ese contraste, explícala por sí sola."),
}
_REFERENCIAS = (
    "\n- Lo que ya trabajó (dato del sílabo, no del CONTEXTO): {temas}. Si el tema de ahora se relaciona con alguno, "
    "apóyate en ello con una frase breve y enlázalo con lo que explicas; no le atribuyas datos que el CONTEXTO no traiga.")

# Lo último que lee un modelo pequeño pesa más que lo de en medio del prompt: el ajuste se repite, muy corto, en el
# recordatorio final (junto al del modo). Los dos se derivan del mismo nivel y estilo, así que siguen a `segmento`.
_RECORDATORIO_NIVEL = {
    "bajo": "abre con una analogía cotidiana breve (sin inventar datos) y cierra con una pregunta sencilla",
    "alto": "ve directo al concepto y cierra con una pregunta socrática exigente (un porqué o un «qué pasaría si…»), "
            "no de repaso",
}
_RECORDATORIO_ESTILO = {
    "ejemplos": "incluye una situación concreta de un proyecto de software",
    "comparativo": "contrasta con otra norma solo si el CONTEXTO la describe, sin trasladar rasgos de una a otra",
}

_EXIGENCIA = {"bajo": "sencilla", "alto": "exigente"}


@dataclass(frozen=True)
class Adaptacion:
    """Lo que el perfil aporta a una respuesta. Con los valores por defecto no aporta nada (prompt de siempre)."""
    texto: str = ""                              # bloque del prompt; "" si no hay ajuste
    recordatorio: str = ""                       # versión corta del ajuste para el recordatorio final del prompt
    segmento: str = ""                           # clave de caché: qué ajuste lleva la respuesta
    personal: bool = False                       # depende del historial de esta persona: no se comparte ni se guarda
    nivel: str = "medio"                         # franja efectiva: bajo | medio | alto
    profundidad: str = "media"                   # la que se aplica a esta respuesta (una tarea no cambia de extensión)
    estilo: str = "conceptual"
    dificultad: bool = False
    referencias: tuple[tuple[str, str, int], ...] = ()   # (tema_id, tema, unidad) de lo ya trabajado que se cita

    @property
    def exigencia(self) -> str:
        """Cómo debe ser la pregunta de reflexión de cierre: sencilla | normal | exigente."""
        return _EXIGENCIA.get(self.nivel, "normal")

    def como_dict(self) -> dict:
        return {"nivel": self.nivel, "profundidad": self.profundidad, "estilo": self.estilo,
                "dificultad": self.dificultad, "segmento": self.segmento,
                "referencias": [{"tema_id": t, "tema": n, "unidad": u} for t, n, u in self.referencias]}


def segmento_de(nivel: str, profundidad: str, estilo: str, dificultad: bool) -> str:
    """Clave de caché del ajuste realmente aplicado (orden fijo: n=, p=, e=, d=; solo las partes no neutras).
    Aparte para que quien recorta la profundidad DESPUÉS de construir la Adaptación (rag_service, por poco
    contexto recuperado: ver tutor.nivel_de_contexto) pueda recalcular el segmento con la profundidad final,
    y no con la preferida del perfil: el caché debe guardar bajo el ajuste que de verdad generó la respuesta."""
    partes = []
    if nivel != "medio":
        partes.append(f"n={nivel}")
    if profundidad != "media":
        partes.append(f"p={profundidad}")
    if estilo != "conceptual":
        partes.append(f"e={estilo}")
    if dificultad:
        partes.append("d=1")
    return "|".join(partes)


def construir_adaptacion(perfil: PerfilEstudiante | None, ubicacion, intencion: str = tutor.PUNTUAL) -> Adaptacion:
    """Ajuste del prompt para este estudiante en esta consulta. `ubicacion` es la unidad/tema de la consulta (dict o
    Ubicacion; None si no se conoce: entonces el nivel se toma como medio y no se citan temas). Sin perfil, neutro."""
    if perfil is None:
        return Adaptacion()
    ub = _ubic(ubicacion)
    unidad = ub["unidad"] if ub else None
    tema_id = ub["tema_id"] if ub else None
    dificultad = tema_id is not None and tema_id in perfil.temas_con_dificultad
    nivel = "bajo" if dificultad else perfil.franja(unidad)
    estilo, preferida = perfil.estilo_preferido, perfil.profundidad_preferida
    referencias = tuple(
        (t.tema_id, t.tema, t.unidad) for t in reversed(perfil.historial_resumido)
        if unidad is not None and t.unidad == unidad and t.tema_id != tema_id)[:MAX_REFERENCIAS]

    con_cierre = intencion != tutor.TAREA
    lineas = [_ANDAMIAJE.get(nivel, "") + (_CIERRE.get(nivel, "") if con_cierre else "")]
    lineas.append((_DIFICULTAD + (_CIERRE_DIFICULTAD if con_cierre else "")) if dificultad else "")
    lineas.append(_ESTILOS.get(estilo, ""))
    if referencias:
        lineas.append(_REFERENCIAS.format(temas="; ".join(f"«{n}» (Unidad {u})" for _, n, u in referencias)))
    cuerpo = "".join(lineas)
    # Una tarea siempre lleva sus pasos numerados: la extensión preferida no cambia esa forma
    profundidad = "media" if intencion == tutor.TAREA else preferida
    texto = _CABECERA + cuerpo if cuerpo or profundidad != "media" else ""

    recordar = [_RECORDATORIO_NIVEL.get(nivel, ""), _RECORDATORIO_ESTILO.get(estilo, "")]
    recordatorio = f" Para este estudiante: {'; '.join(r for r in recordar if r)}." if con_cierre and any(recordar) else ""

    # segmento con `profundidad` (ya ajustada a TAREA), no con `preferida`: para una tarea el prompt siempre
    # explica el modo TAREA sin importar la profundidad del perfil, así que dos tareas con distinta profundidad
    # preferida generaban el mismo prompt pero un segmento de caché distinto (fallo silencioso: solo perdía
    # aciertos, nunca servía contenido equivocado, pero fragmentaba el caché sin motivo).
    segmento = segmento_de(nivel, profundidad, estilo, dificultad)
    return Adaptacion(texto=texto, recordatorio=recordatorio, segmento=segmento, personal=bool(referencias), nivel=nivel,
                      profundidad=profundidad, estilo=estilo, dificultad=dificultad, referencias=referencias)

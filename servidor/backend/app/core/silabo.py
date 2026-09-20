"""Temario de la asignatura Normativas de Ingeniería de Software (sílabo oficial, PAO 2026 B).

Fuente: 7mo-NormativasSoftware-A-signed.pdf (Universidad Politécnica del Carchi). Se usa para
decidir si una pregunta es pertinente y para proponer temas al redirigir al estudiante.
Este temario cubre más que los documentos indexados (p. ej. métricas o Scrum no tienen fuente
en documentacion/): una pregunta sobre ellos es del ámbito aunque el RAG no tenga contexto.
"""

UNIDADES_SILABO: list[dict] = [
    {
        "numero": 1,
        "titulo": "Aplicación de metodología de desarrollo de software",
        "temas": [
            "marcos predictivos, iterativos, ágiles e híbridos",
            "Scrum, Kanban y Lean",
            "requisitos ágiles (backlog, historias de usuario, criterios de aceptación)",
            "ciclo de vida del desarrollo de software (SDLC)",
            "DevOps y DevSecOps",
            "gobierno de procesos y mejora continua",
        ],
    },
    {
        "numero": 2,
        "titulo": "Normativas de desarrollo y calidad del software",
        "temas": [
            "fundamentos de normas ISO/IEC/IEEE: estándares, certificación, acreditación, auditoría y cumplimiento",
            "ISO 9001 (gestión de la calidad)",
            "ISO/IEC/IEEE 12207 (ciclo de vida del software)",
            "madurez de procesos: CMMI e ISO/IEC 33000 (SPICE)",
            "ISO/IEC 25000 (SQuaRE) e ISO/IEC 25010 (calidad del producto)",
            "seguridad, privacidad e IA: ISO/IEC 27001, 27002, desarrollo seguro, ISO/IEC 42001 y gobierno de IA",
            "ISO/IEC 20000 (gestión de servicios de TI), ISO/IEC 29110 (pequeñas organizaciones), "
            "ISO 31000 (gestión de riesgos) e ISO/IEC/IEEE 42010 (arquitectura)",
        ],
    },
    {
        "numero": 3,
        "titulo": "Métricas de gestión de proyectos de software",
        "temas": [
            "fundamentos de medición: KPIs y líneas base",
            "tamaño, esfuerzo y estimación (puntos de función, story points, velocidad)",
            "métricas de calidad del producto (ISO/IEC 25010)",
            "métricas ágiles y de flujo (lead time, cycle time, WIP, diagrama de flujo acumulado)",
            "métricas DORA de DevOps",
            "métricas de experiencia de usuario, seguridad y sostenibilidad; tableros",
        ],
    },
    {
        "numero": 4,
        "titulo": "Gestión de pruebas, implementación y mantenimiento",
        "temas": [
            "verificación y validación, niveles de prueba, ISO/IEC/IEEE 29119",
            "TDD, automatización, análisis estático y quality gates",
            "CI/CD, gestión de la configuración y contenedores",
            "mantenimiento y evolución (ISO/IEC/IEEE 14764, refactorización, deuda técnica)",
            "operación, observabilidad y gestión de incidentes",
        ],
    },
]


def temas_planos() -> list[str]:
    """Todos los temas del sílabo como líneas 'Unidad N: tema' (índice = número - 1)."""
    return [f"Unidad {u['numero']}: {tema}" for u in UNIDADES_SILABO for tema in u["temas"]]


def ubicar_en_silabo(termino: str) -> list[str]:
    """Dónde trata el sílabo un término (p. ej. 'Scrum' -> Unidad 1, 'ISO/IEC/IEEE 29119' -> Unidad 4).
    Devuelve líneas 'Unidad N (título): tema'. Es la ubicación real, para no depender de que el LLM
    adivine la unidad correcta."""
    import re
    import unicodedata

    def norm(t: str) -> str:
        t = "".join(c for c in unicodedata.normalize("NFKD", t.lower()) if not unicodedata.combining(c))
        return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", t)).strip()

    buscado = norm(termino)
    if not buscado:
        return []
    return [
        f"Unidad {u['numero']} ({u['titulo']}): {tema}"
        for u in UNIDADES_SILABO for tema in u["temas"] if buscado in norm(tema)
    ]


def texto_temas_numerados() -> str:
    return "\n".join(f"{i}. {t}" for i, t in enumerate(temas_planos(), start=1))


def texto_silabo(con_temas: bool = True) -> str:
    """Temario en texto plano, para incluir en los prompts."""
    lineas = []
    for u in UNIDADES_SILABO:
        lineas.append(f"Unidad {u['numero']}: {u['titulo']}")
        if con_temas:
            lineas.extend(f"  - {tema}" for tema in u["temas"])
    return "\n".join(lineas)

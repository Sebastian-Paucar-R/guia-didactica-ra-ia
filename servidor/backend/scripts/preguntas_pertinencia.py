"""Preguntas reales para calibrar y evaluar el filtro de pertinencia (dentro / fuera del temario)."""

# Dentro del temario. Las marcadas "sin doc" pertenecen al sílabo pero no tienen documento indexado
# (el RAG no tendrá buen contexto: el filtro no debe redirigirlas).
DENTRO = [
    "¿Qué es la ISO 9001 y para qué sirve?",
    "¿Cuáles son las características de calidad de ISO/IEC 25010?",
    "¿Qué diferencia hay entre ISO 27001 e ISO 27002?",
    "¿Cómo se gestionan los riesgos según ISO 31000?",
    "¿Qué procesos define la ISO/IEC 12207 para el ciclo de vida del software?",
    "¿Qué niveles de capacidad de proceso tiene ISO/IEC 33000?",
    "¿Para qué sirve ISO/IEC 29110 en una empresa pequeña de software?",
    "¿Qué es un sistema de gestión de seguridad de la información?",
    "no entiendo lo de mantenibilidad en la 25010, me lo explicas?",
    "¿Qué necesito para certificar mi empresa de software en una norma ISO?",
    "¿Cómo se hace una auditoría interna de calidad?",
    "¿Qué es Scrum y cuáles son sus roles?",                       # sin doc
    "¿Qué son las métricas DORA de DevOps?",                       # sin doc
    "¿Qué es la deuda técnica y cómo afecta al mantenimiento?",    # sin doc
    "¿Qué es el desarrollo guiado por pruebas (TDD)?",             # sin doc
    "¿Cómo se estima el esfuerzo de un proyecto con puntos de función?",  # sin doc
    # Segunda tanda (añadida tras la primera evaluación, para no ajustar el prompt solo a un caso)
    "¿Qué es una auditoría de certificación y en qué se diferencia de una interna?",
    "¿Qué es la mejora continua en un sistema de gestión?",
    "¿Cómo se gestionan los incidentes en producción?",              # sin doc
    "¿Qué es CI/CD y por qué importa?",                              # sin doc
    "¿Qué es CMMI?",                                                 # sin doc
    "¿Qué significa aseguramiento de la calidad de software?",
    "¿Cuál es la diferencia entre verificación y validación?",       # sin doc
    "¿Cómo defino un backlog y criterios de aceptación?",            # sin doc
]

# Claramente fuera del temario.
FUERA = [
    "¿Cómo preparo una receta de pastel de chocolate?",
    "¿Quién ganó el mundial de fútbol de 2022?",
    "¿Cuál es la capital de Australia?",
    "¿Me recomiendas una película de ciencia ficción para este fin de semana?",
    "¿Cómo se resuelve una ecuación de segundo grado?",
    "¿Qué síntomas tiene la gripe y cómo se cura?",
    "¿Cómo hago un bucle for en Python?",
    "Explícame la teoría de la relatividad",
    "¿Cuánto es 25 por 48?",
    "¿Qué lugares turísticos me recomiendas visitar en Cusco?",
    "¿Cómo puedo aprender a tocar la guitarra?",
    "¿Cómo invierto mis ahorros en la bolsa de valores?",
    "¿Cómo funciona la fotosíntesis?",
    "Cuéntame sobre la Revolución Francesa",
    "¿Cuál es la mejor manera de bajar de peso?",
    "¿Cómo se calcula la derivada de x al cuadrado?",
    "¿Cuál es el mejor teléfono para comprar este año?",
    "Escríbeme un poema sobre el mar",
    # Categorías que no se mencionan en el prompt del clasificador
    "¿Cómo cuido a mi perro cachorro?",
    "¿Cuál es la historia del imperio inca?",
    "¿Quién es el mejor cantante de rock de los años 80?",
    "¿Cómo se prepara el ceviche?",
]

# Casos límite: ni dentro ni fuera de forma evidente (no cuentan en las métricas, se observan).
LIMITE = [
    "¿Cómo protejo mi cuenta de Instagram de los hackers?",
    "¿Qué es un pull request en Git?",
    "¿Cómo organizo mejor mi tiempo para estudiar para los exámenes?",
]

# Preguntas sobre el funcionamiento del propio tutor (siempre pasan sin filtro).
SOBRE_TUTOR = [
    "¿Qué puedes hacer?",
    "¿Qué documentos tienes?",
    "¿De qué temas me puedes ayudar?",
    "¿Con qué normas puedes ayudarme?",
    "quién eres y cómo funcionas",
]

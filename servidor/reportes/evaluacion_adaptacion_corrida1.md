# Evaluación de la adaptación al estudiante

Generado por `pruebas/evaluar_adaptacion.py` el 2026-09-20 06:40 contra `http://127.0.0.1:8000` — **llama3.2-real-v1**.

Tres estudiantes con perfiles distintos hacen la misma pregunta. Se espera que las respuestas **difieran en la forma** (extensión, andamiaje, estilo, cierre) y **coincidan en el contenido normativo**. Los verdictos son heurísticos (regex y similitud de texto): las respuestas están completas debajo para leerlas.

## Estudiantes

| Estudiante | Perfil sembrado |
|---|---|
| **novato** | Nivel bajo en la Unidad 2 (1,8), prefiere explicaciones extensas y con ejemplos. Solo ha visto Scrum (otra unidad): nada que citar. |
| **estandar** | Estudiante nuevo: perfil inicial (nivel 3, profundidad media, estilo conceptual). Recibe el prompt de siempre y comparte el caché con los anónimos. |
| **avanzado** | Nivel alto en la Unidad 2 (4,6), prefiere respuestas breves y comparativas. Ya trabajó ISO 9001 e ISO/IEC 25010 (misma unidad): el tutor puede apoyarse en ello. |

## Resumen de verdictos automáticos

| Pregunta | Contenido normativo | Forma distinta | Ajustes distintos | Caché por segmento |
|---|---|---|---|---|
| A1 «¿Qué es ISO 9001?» | ✅ | ✅ | ✅ | ✅ |
| A2 «¿Qué es ISO/IEC 25010?» | ✅ | ✅ | ✅ | ✅ |
| A3 «¿Qué es ISO/IEC/IEEE 12207?» | ✅ | ✅ | ✅ | ✅ |

## A1 · «¿Qué es ISO 9001?» (tema 2.2)

| | **novato** | **estandar** | **avanzado** |
|---|---|---|---|
| Ajuste aplicado | `n=bajo|p=extensa|e=ejemplos` | `ninguno` | `n=alto|p=breve|e=comparativo` |
| Cita lo ya trabajado | — | — | 2.5 |
| Respuesta | ISO 9001 es la norma internacional más adoptada en el mundo para Sistemas de Gestión de la Calidad (SGC). Aunque no fue creada específicamente para software, es ampliamente utilizada por empresas de tecnología y desarrollo de software como marco general de gestión de calidad organizacional. Es importante que un estudiante de Informática comprenda esta norma porque muchas empresas de TI la exigen como requisito para participar en licitaciones o contratos, y porque introduce el vocabulario y los principios de gestión de calidad que también sustentan otras normas ISO.<br><br>ISO 9001 proporciona una estructura general para la gestión de la calidad organizacional, enfocada en la satisfacción del cliente. Requiere que las empresas establezcan un sistema de gestión de la calidad que incluya políticas, procedimientos y controles para garantizar la calidad de sus productos o servicios.<br><br>La certificación ISO 9001 es otorgada por organismos de certificación acreditados, mediante auditorías externas periódicas. La norma también se relaciona con otras normas como ISO/IEC 27001 (seguridad de la información), ISO/IEC 12207 (procesos del ciclo de vida del software) e ISO/IEC 25010 (calidad del producto de software).<br><br>¿Cómo abordarías una auditoría de calidad en un proyecto de desarrollo de software certificado con ISO 9001? | ISO 9001 es la norma internacional más adoptada en el mundo para Sistemas de Gestión de la Calidad (SGC). Aunque no fue creada específicamente para software, es ampliamente utilizada por empresas de tecnología y desarrollo de software como marco general de gestión de calidad organizacional. La certificación ISO 9001 otorgada por organismos de certificación acreditados permite a las empresas demostrar su compromiso con la calidad y sus procesos de gestión.<br><br>¿Cómo se relaciona esta norma con el "pensamiento basado en riesgos" que exigen otras normas como ISO 9001, ISO/IEC 27001 o ISO/IEC 20000? | ISO 9001 es un estándar internacional para Sistemas de Gestión de la Calidad (SGC) que proporciona principios, un marco de referencia y un proceso genérico para gestionar la calidad en cualquier tipo de organización. Es una norma de directrices guía, no certificable, pero su aplicación es obligatoria en muchas empresas de TI como requisito para participar en licitaciones o contratos.<br><br>¿Qué pasaría si una empresa de desarrollo de software no tuviera un sistema de gestión de calidad basado en ISO 9001? |
| Palabras | 198 | 93 | 81 |
| Normas que nombra | ISO 9001, ISO/IEC 12207, ISO/IEC 25010, ISO/IEC 27001 | ISO 9001, ISO/IEC 20000, ISO/IEC 27001 | ISO 9001 |
| Normas/años sin respaldo en los documentos | ninguno | ninguno | ninguno |
| Ideas ancla que faltan | ninguna | ninguna | ninguna |
| Marca de analogía/situación | ✅ | ❌ | ❌ |

Similitud de texto entre pares (1 = idéntico; umbral de «distintas» < 0.8): novato~estandar = 0.34, novato~avanzado = 0.18, estandar~avanzado = 0.18. El avanzado cierra en pregunta: ✅; con marca socrática: ✅.

**Segunda vez, conversación nueva (caché):** novato: desde caché, estandar: desde caché, avanzado: generada, anonimo: desde caché. Recibió lo suyo: {novato: ✅, estandar: ✅, avanzado: ❌}; recibió la respuesta de otro estudiante: ninguno; el anónimo recibe lo del estándar: ✅.

## A2 · «¿Qué es ISO/IEC 25010?» (tema 2.5)

| | **novato** | **estandar** | **avanzado** |
|---|---|---|---|
| Ajuste aplicado | `n=bajo|p=extensa|e=ejemplos` | `ninguno` | `n=alto|p=breve|e=comparativo` |
| Cita lo ya trabajado | — | — | 2.2 |
| Respuesta | ISO/IEC 25010 es un estándar de calidad de producto de software que define los requisitos y criterios para la evaluación de la calidad del producto. En este contexto, ISO 9001 proporciona el marco general para la gestión de la calidad en las organizaciones, incluyendo aquellas que desarrollan software. La norma ISO/IEC 25010 se utiliza para evaluar la calidad del producto de software y garantizar que cumpla con los requisitos establecidos por la organización o el cliente.<br><br>ISO/IEC 29110 proporciona un perfil específico para entidades de software pequeñas, como las empresas VSE (Small and Medium-sized Enterprises), pero no define directamente la calidad del producto. En cambio, se enfoca en la gestión y los procesos de desarrollo del software. Por lo tanto, ISO/IEC 25010 es una norma que complementa a ISO 9001 y proporciona un marco para evaluar específicamente la calidad del producto de software.<br><br>¿Cómo relacionarías estos estándares con el gobierno de procesos en un proyecto de desarrollo de software? | ISO/IEC 25010 es un estándar de calidad del producto de software que describe los requisitos y recomendaciones para la medición, evaluación y descripción de la calidad del producto de software. En otras palabras, se ocupa de cómo evaluar el rendimiento y la calidad de un programa informático.<br><br>¿Cuál es su aplicación en práctica? | ISO/IEC 25010 es un estándar de calidad de producto de software que describe los requisitos para la gestión de la calidad en el desarrollo y mantenimiento de sistemas de software. Se enfoca en proporcionar una base común para evaluar y mejorar la calidad del producto, complementando las normas ISO/IEC 12207 e ISO 9001.<br><br>¿Qué relación tiene este estándar con la adaptación de procesos estándar a un contexto específico? |
| Palabras | 159 | 53 | 68 |
| Normas que nombra | ISO 9001, ISO/IEC 25010, ISO/IEC 29110 | ISO/IEC 25010 | ISO 9001, ISO/IEC 12207, ISO/IEC 25010 |
| Normas/años sin respaldo en los documentos | ninguno | ninguno | ninguno |
| Ideas ancla que faltan | ninguna | ninguna | ninguna |
| Marca de analogía/situación | ✅ | ❌ | ❌ |

Similitud de texto entre pares (1 = idéntico; umbral de «distintas» < 0.8): novato~estandar = 0.12, novato~avanzado = 0.15, estandar~avanzado = 0.29. El avanzado cierra en pregunta: ✅; con marca socrática: ✅.

**Segunda vez, conversación nueva (caché):** novato: desde caché, estandar: desde caché, avanzado: generada, anonimo: desde caché. Recibió lo suyo: {novato: ✅, estandar: ✅, avanzado: ❌}; recibió la respuesta de otro estudiante: ninguno; el anónimo recibe lo del estándar: ✅.

## A3 · «¿Qué es ISO/IEC/IEEE 12207?» (tema 2.3)

| | **novato** | **estandar** | **avanzado** |
|---|---|---|---|
| Ajuste aplicado | `n=bajo|p=extensa|e=ejemplos` | `ninguno` | `n=alto|p=breve|e=comparativo` |
| Cita lo ya trabajado | — | — | 2.5, 2.2 |
| Respuesta | ISO/IEC 12207 es un estándar de la organización internacional ISO-IEC que define los procesos del ciclo de vida del software, especificando cómo se deben llevar a cabo las actividades relacionadas con el desarrollo, implementación y mantenimiento de sistemas de software. Este estándar establece una estructura general para los procesos del ciclo de vida del software, incluyendo la planificación, la ejecución, la verificación y la revisión. En particular, ISO/IEC 12207 define tres niveles de madurez en las organizaciones que implementan estos procesos: nivel A (madera), nivel B (pino) y nivel C (roble). Por otro lado, el documento «ISO/IEC 42010 — Descripción de la Arquitectura de Sistemas y Software» establece una arquitectura general para sistemas y software que puede ser utilizada como base para los procesos del ciclo de vida del software. ¿Cómo aplicaría el estándar ISO/IEC 12207 a su próximo proyecto de desarrollo de software? | ISO/IEC 12207 es un estándar que define los procesos del ciclo de vida del software, especificando las actividades y responsabilidades involucradas en cada fase. En otras palabras, describe cómo se lleva a cabo el desarrollo, implementación y mantenimiento de sistemas de software. Este estándar proporciona una estructura común para la industria, permitiendo que los proyectos sigan procesos similares y sean evaluados de manera comparativa.<br><br>¿Cómo relacionas este concepto con las normas de calidad del producto? | ISO/IEC 12207 es un estándar que describe los procesos del ciclo de vida del software, mientras que ISO/IEC 42010 define la descripción de la arquitectura de sistemas y software. Ambas normas se relacionan con el proceso de "diseño de arquitectura" que produce una descripción de arquitectura.<br><br>¿Qué pasaría si un proyecto de desarrollo de software no tuviera una descripción clara de su arquitectura? |
| Palabras | 144 | 75 | 63 |
| Normas que nombra | ISO/IEC 12207, ISO/IEC 42010 | ISO/IEC 12207 | ISO/IEC 12207, ISO/IEC 42010 |
| Normas/años sin respaldo en los documentos | ninguno | ninguno | ninguno |
| Ideas ancla que faltan | ninguna | ninguna | ninguna |
| Marca de analogía/situación | ✅ | ❌ | ✅ |

Similitud de texto entre pares (1 = idéntico; umbral de «distintas» < 0.8): novato~estandar = 0.06, novato~avanzado = 0.12, estandar~avanzado = 0.11. El avanzado cierra en pregunta: ✅; con marca socrática: ✅.

**Segunda vez, conversación nueva (caché):** novato: desde caché, estandar: desde caché, avanzado: generada, anonimo: desde caché. Recibió lo suyo: {novato: ✅, estandar: ✅, avanzado: ❌}; recibió la respuesta de otro estudiante: ninguno; el anónimo recibe lo del estándar: ✅.

## Evolución de un estudiante real

Un estudiante real (sin perfil sembrado) que dice no entender y pide ejemplos. El perfil debe moverse poco a poco y por lo que hace, no por lo que dice de sí mismo.

| Turno | Mensaje | Nivel U2 | Estilo | Profundidad | Temas con dificultad |
|---|---|---|---|---|---|
| 0 | (perfil inicial) | 3.0 | conceptual | media | — |
| 1 | ¿Qué es ISO 9001? | 3.0 | conceptual | media | — |
| 2 | No entendí, explícame eso mejor | 2.6 | conceptual | media | 2.2 |
| 3 | Sigo sin entender, explícamelo otra vez | 2.6 | conceptual | media | 2.2 |
| 4 | Dame un ejemplo | 2.6 | conceptual | media | 2.2 |
| 5 | Dame otro ejemplo | 2.6 | conceptual | media | 2.2 |
| 6 | Muéstrame un ejemplo con un equipo pequeño | 2.6 | conceptual | media | 2.2 |

Progreso de la Unidad 2 (`GET /perfil/{id}/progreso`): 3.0 (inicial) → 2.6 (confusion).

Al volver a preguntar «¿Qué es ISO 9001?» en otra conversación el ajuste fue `n=bajo|d=1` (nivel bajo, estilo conceptual, dificultad True).

| Verdicto | |
|---|---|
| el nivel solo baja y sin saltos | ✅ |
| bajo al menos un paso | ✅ |
| no entendi marca dificultad | ✅ |
| estilo pasa a ejemplos | ❌ |
| progreso coincide con el nivel | ✅ |
| la siguiente respuesta se adapta | ❌ |
| reiniciar limpia | ✅ |

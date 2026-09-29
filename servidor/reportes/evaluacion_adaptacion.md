# Evaluación de la adaptación al estudiante

Generado por `pruebas/evaluar_adaptacion.py` el 2026-09-29 10:50 contra `http://127.0.0.1:8020` — **ronda oficial 2026-09-29 (correcciones aplicadas)**.

Tres estudiantes con perfiles distintos hacen la misma pregunta. Se espera que las respuestas **difieran en la forma** (extensión, andamiaje, estilo, cierre) y **coincidan en el contenido normativo**. Los verdictos son heurísticos (regex y similitud de texto): las respuestas están completas debajo para leerlas.

## Estudiantes

| Estudiante | Perfil sembrado |
|---|---|
| **novato** | Nivel bajo en la Unidad 2 (1,8), prefiere explicaciones extensas y con ejemplos. Solo ha visto Scrum (otra unidad): nada que citar. |
| **estandar** | Estudiante nuevo: perfil inicial (nivel 3, profundidad media, estilo conceptual). Recibe el prompt de siempre y comparte el caché con los anónimos. |
| **avanzado** | Nivel alto en la Unidad 2 (4,6), prefiere respuestas breves y comparativas. Ya trabajó ISO 9001 e ISO/IEC 25010 (misma unidad): el tutor puede apoyarse en ello. |

## Resumen de verdictos automáticos

| Pregunta | Contenido normativo | Mismas normas en los tres | Forma distinta | Ajustes distintos | Caché por segmento |
|---|---|---|---|---|---|
| A1 «¿Qué es ISO 9001?» | ❌ | ❌ | ✅ | ✅ | ✅ |
| A2 «¿Qué es ISO/IEC 25010?» | ❌ | ❌ | ✅ | ✅ | ✅ |
| A3 «¿Qué es ISO/IEC/IEEE 12207?» | ❌ | ❌ | ✅ | ✅ | ✅ |

## A1 · «¿Qué es ISO 9001?» (tema 2.2)

| | **novato** | **estandar** | **avanzado** |
|---|---|---|---|
| Ajuste aplicado | `n=bajo|p=extensa|e=ejemplos` | `ninguno` | `n=alto|p=breve|e=comparativo` |
| Cita lo ya trabajado | — | — | 2.5 |
| Respuesta | Imagina que tienes un proyecto de software que desarrollarás con un equipo de 5 personas y quieres asegurarte de que todo salga bien. Para lograrlo, decides establecer ciertos estándares para el desarrollo, como la calidad del código, la gestión de cambios y la satisfacción del cliente. Estos estándares se basan en las directrices proporcionadas por ISO 9001:2015 — Sistemas de Gestión de la Calidad. En este sentido, ISO 9001 se convierte en una especie de "paraguas" bajo el cual se integran prácticas específicas de calidad de software. La certificación ISO 9001 es otorgada por organismos de certificación acreditados y requiere auditorías externas periódicas. ¿Cómo integraría los estándares ISO 9001 en tu próximo proyecto de desarrollo de software? | ISO 9001 es la norma internacional más adoptada en el mundo para Sistemas de Gestión de la Calidad (SGC). Aunque no fue creada específicamente para software, es ampliamente utilizada por empresas de tecnología y desarrollo de software como marco general de gestión de calidad organizacional. La certificación ISO 9001 es otorgada por organismos de certificación acreditados, mediante auditorías externas periódicas.<br><br>¿Cómo se relaciona la gestión de riesgos con la gestión de calidad en el contexto del desarrollo de software? | ISO 9001 es la norma internacional más adoptada en el mundo para Sistemas de Gestión de la Calidad (SGC). Aunque no fue creada específicamente para software, es ampliamente utilizada por empresas de tecnología y desarrollo de software como marco general de gestión de calidad organizacional. ¿Qué pasaría si una empresa de software implementara ISO 9001 sin considerar las necesidades específicas de su proyecto? |
| Palabras | 117 | 79 | 63 |
| Normas que nombra | ISO 9001, ISO 9001:2015 | ISO 9001 | ISO 9001 |
| ...no comunes a los tres (posible atribución cruzada) | ISO 9001:2015 | — | — |
| Normas/años sin respaldo en los documentos | ninguno | ninguno | ninguno |
| Ideas ancla que faltan | ninguna | ninguna | ninguna |
| Afirmaciones que los documentos contradicen | ninguna | ninguna | ninguna |
| Marca de analogía/situación | ✅ | ❌ | ✅ |

Similitud de texto entre pares (1 = idéntico; umbral de «distintas» < 0.8): novato~estandar = 0.14, novato~avanzado = 0.13, estandar~avanzado = 0.65. El avanzado cierra en pregunta: ✅; con marca socrática: ✅.

**Segunda vez, conversación nueva (caché):** novato: desde caché, estandar: desde caché, avanzado: generada, anonimo: desde caché. Recibió lo suyo: {novato: ✅, estandar: ✅, avanzado: ❌}; recibió la respuesta de otro estudiante: ninguno; el anónimo recibe lo del estándar: ✅.

## A2 · «¿Qué es ISO/IEC 25010?» (tema 2.5)

| | **novato** | **estandar** | **avanzado** |
|---|---|---|---|
| Ajuste aplicado | `n=bajo|p=extensa|e=ejemplos` | `ninguno` | `n=alto|p=breve|e=comparativo` |
| Cita lo ya trabajado | — | — | 2.2 |
| Respuesta | La calidad del producto de software es como un edificio en construcción: cada pieza debe estar bien hecha y encajar con las demás para crear una estructura sólida. ¿Cómo garantizarás que cada componente del sistema funcione correctamente antes de integrarlos en el edificio final? | Por lo tanto, no puedo ofrecer una explicación detallada sobre este estándar dentro del contexto dado. ¿Cuál es tu comprensión general de cómo las normas como ISO 9001 y su relación con la calidad de software? | Se trata de una norma específica en el contexto de gestión de calidad, complementando a ISO 9001. ¿Qué normas específicas se aplicarían en una empresa que desarrolla software y busca mejorar su calidad? |
| Palabras | 44 | 36 | 33 |
| Normas que nombra | — | ISO 9001 | ISO 9001 |
| ...no comunes a los tres (posible atribución cruzada) | — | ISO 9001 | ISO 9001 |
| Normas/años sin respaldo en los documentos | ninguno | ninguno | ninguno |
| Ideas ancla que faltan | 25010 | 25010 | 25010 |
| Afirmaciones que los documentos contradicen | ninguna | ninguna | ninguna |
| Marca de analogía/situación | ✅ | ❌ | ❌ |

Similitud de texto entre pares (1 = idéntico; umbral de «distintas» < 0.8): novato~estandar = 0.06, novato~avanzado = 0.04, estandar~avanzado = 0.07. El avanzado cierra en pregunta: ✅; con marca socrática: ❌.

**Segunda vez, conversación nueva (caché):** novato: desde caché, estandar: desde caché, avanzado: generada, anonimo: desde caché. Recibió lo suyo: {novato: ✅, estandar: ✅, avanzado: ❌}; recibió la respuesta de otro estudiante: ninguno; el anónimo recibe lo del estándar: ✅.

## A3 · «¿Qué es ISO/IEC/IEEE 12207?» (tema 2.3)

| | **novato** | **estandar** | **avanzado** |
|---|---|---|---|
| Ajuste aplicado | `n=bajo|p=extensa|e=ejemplos` | `ninguno` | `n=alto|p=breve|e=comparativo` |
| Cita lo ya trabajado | — | — | 2.5, 2.2 |
| Respuesta | ISO/IEC 12207 es como un plan de trabajo en una empresa de construcción. Imagina que tienes un proyecto de software grande y complejo, con muchas partes que deben funcionar juntas. Un plan de trabajo similar a ISO/IEC 12207 te ayuda a organizar todo el proceso del desarrollo del software, desde la definición inicial hasta su lanzamiento final.<br><br>Este plan de trabajo define los procesos estándar que se seguirán durante cada fase del ciclo de vida del software, como la planificación, la implementación y la verificación. De esta manera, puedes asegurarte de que todos los pasos estén bien documentados y que no haya problemas importantes que puedan surgir durante el desarrollo. ¿Cómo definirías los procesos estándar para tu próximo proyecto de software? | ISO/IEC 12207 es un estándar que describe los procesos del ciclo de vida del software. En otras palabras, establece las actividades y tareas necesarias para desarrollar, implementar y mantener sistemas de software. Esto incluye desde la definición de requisitos hasta la entrega final del producto.<br><br>¿En qué relación se relaciona este proceso con el concepto de arquitectura en el contexto de ISO/IEC 42010? | ISO/IEC 12207 es un estándar que define los procesos del ciclo de vida del software, especificando las actividades y responsabilidades involucradas en cada fase del proceso. En otras palabras, describe cómo se desarrolla un proyecto de software desde su inicio hasta su finalización. ¿Por qué considera que ISO/IEC 12207 es importante para el desarrollo de proyectos de software en entornos complejos? |
| Palabras | 121 | 63 | 61 |
| Normas que nombra | ISO/IEC 12207 | ISO/IEC 12207, ISO/IEC 42010 | ISO/IEC 12207 |
| ...no comunes a los tres (posible atribución cruzada) | — | ISO/IEC 42010 | — |
| Normas/años sin respaldo en los documentos | ninguno | ninguno | ninguno |
| Ideas ancla que faltan | ninguna | ninguna | ninguna |
| Afirmaciones que los documentos contradicen | ninguna | ninguna | ninguna |
| Marca de analogía/situación | ✅ | ❌ | ✅ |

Similitud de texto entre pares (1 = idéntico; umbral de «distintas» < 0.8): novato~estandar = 0.07, novato~avanzado = 0.11, estandar~avanzado = 0.16. El avanzado cierra en pregunta: ✅; con marca socrática: ✅.

**Segunda vez, conversación nueva (caché):** novato: desde caché, estandar: desde caché, avanzado: generada, anonimo: desde caché. Recibió lo suyo: {novato: ✅, estandar: ✅, avanzado: ❌}; recibió la respuesta de otro estudiante: ninguno; el anónimo recibe lo del estándar: ✅.

## Evolución de un estudiante real

Un estudiante real (sin perfil sembrado) que dice no entender y pide ejemplos. El perfil debe moverse poco a poco y por lo que hace, no por lo que dice de sí mismo. Los mensajes nombran su tema: un seguimiento pelado («Dame otro ejemplo») depende de que el reformulador del filtro lo entienda y en la primera corrida real el filtro redirigió dos de ellos como fuera de tema (limitación previa al perfil, ver BITACORA).

| Turno | Mensaje | Nivel U2 | Estilo | Profundidad | Temas con dificultad |
|---|---|---|---|---|---|
| 0 | (perfil inicial) | 3.0 | conceptual | media | — |
| 1 | ¿Qué es ISO 9001? | 3.0 | conceptual | media | — |
| 2 | No entendí, explícame eso mejor | 2.6 | conceptual | media | 2.2 |
| 3 | Sigo sin entender ISO 9001, explícamelo otra vez | 2.2 | conceptual | media | 2.2 |
| 4 | Dame un ejemplo de ISO 9001 | 2.2 | conceptual | media | 2.2 |
| 5 | Dame otro ejemplo de ISO 9001 en un equipo pequeño | 2.2 | conceptual | media | 2.2 |
| 6 | Muéstrame un ejemplo más de ISO 9001 en una startup | 2.2 | ejemplos | media | 2.2 |

Progreso de la Unidad 2 (`GET /perfil/{id}/progreso`): 3.0 (inicial) → 2.6 (confusion) → 2.2 (confusion).

Al volver a preguntar «¿Qué es ISO 9001?» en otra conversación el ajuste fue `n=bajo|e=ejemplos|d=1` (nivel bajo, estilo ejemplos, dificultad True).

| Verdicto | |
|---|---|
| el nivel solo baja y sin saltos | ✅ |
| bajo al menos un paso | ✅ |
| no entendi marca dificultad | ✅ |
| estilo pasa a ejemplos | ✅ |
| progreso coincide con el nivel | ✅ |
| la siguiente respuesta se adapta | ✅ |
| reiniciar limpia | ✅ |

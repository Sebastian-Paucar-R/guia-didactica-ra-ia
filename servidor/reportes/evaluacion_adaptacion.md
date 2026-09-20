# Evaluación de la adaptación al estudiante

Generado por `pruebas/evaluar_adaptacion.py` el 2026-09-20 07:13 contra `http://127.0.0.1:8000` — **llama3.2-real-final**.

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
| Respuesta | Imagina que estás trabajando en un equipo de desarrollo de software y necesitas cumplir con las expectativas de tus clientes. Para asegurarte de que todo salga bien, decides implementar un sistema de gestión de calidad (SGC) que te ayude a controlar los procesos y garantizar la satisfacción del cliente. Este SGC es lo que se refiere a ISO 9001 — Sistemas de Gestión de la Calidad. La norma proporciona una guía para implementar un sistema de gestión de calidad en cualquier organización, incluyendo empresas de desarrollo de software.<br><br>ISO 9001 no solo se enfoca en la calidad del producto, sino que también aborda aspectos como la seguridad de la información y el gobierno de riesgos. Por ejemplo, si una empresa de TI tiene una certificación en ISO 27001, esto significa que ha implementado un sistema de gestión integrado de calidad y seguridad para proteger sus datos y mantener la confidencialidad.<br><br>La relación entre ISO 9001 y otras normas es importante: por ejemplo, ISO/IEC 12207 proporciona detalles técnicos específicos sobre los procesos del ciclo de vida del software que complementan el enfoque general de gestión de calidad introducido en ISO 9001. ¿Cómo implementaría ISO 9001 en tu proyecto actual para garantizar la calidad del producto final? | ISO 9001 es un estándar internacional para Sistemas de Gestión de la Calidad (SGC) que proporciona principios, un marco de referencia y un proceso genérico para gestionar la calidad en cualquier tipo de organización. Aunque no fue creado específicamente para software, se utiliza ampliamente por empresas de tecnología y desarrollo de software como marco general de gestión de calidad organizacional. La certificación ISO 9001 es otorgada por organismos de certificación acreditados mediante auditorías externas periódicas.<br><br>¿Cómo relaciona la comprensión de esta norma con el desarrollo de software? | ISO 9001 es la norma internacional más adoptada en el mundo para Sistemas de Gestión de la Calidad (SGC). Aunque no fue creada específicamente para software, es ampliamente utilizada por empresas de tecnología y desarrollo de software como marco general de gestión de calidad organizacional. ¿Qué pasaría si una empresa de software aplicara ISO 9001 a su proyecto sin ajustar adecuadamente sus procesos? |
| Palabras | 205 | 87 | 63 |
| Normas que nombra | ISO 27001, ISO 9001, ISO/IEC 12207 | ISO 9001 | ISO 9001 |
| Normas/años sin respaldo en los documentos | ninguno | ninguno | ninguno |
| Ideas ancla que faltan | ninguna | ninguna | ninguna |
| Afirmaciones que los documentos contradicen | ninguna | ninguna | ninguna |
| Marca de analogía/situación | ✅ | ❌ | ✅ |

Similitud de texto entre pares (1 = idéntico; umbral de «distintas» < 0.8): novato~estandar = 0.06, novato~avanzado = 0.06, estandar~avanzado = 0.45. El avanzado cierra en pregunta: ✅; con marca socrática: ✅.

**Segunda vez, conversación nueva (caché):** novato: desde caché, estandar: desde caché, avanzado: generada, anonimo: desde caché. Recibió lo suyo: {novato: ✅, estandar: ✅, avanzado: ❌}; recibió la respuesta de otro estudiante: ninguno; el anónimo recibe lo del estándar: ✅.

## A2 · «¿Qué es ISO/IEC 25010?» (tema 2.5)

| | **novato** | **estandar** | **avanzado** |
|---|---|---|---|
| Ajuste aplicado | `n=bajo|p=extensa|e=ejemplos` | `ninguno` | `n=alto|p=breve|e=comparativo` |
| Cita lo ya trabajado | — | — | 2.2 |
| Respuesta | La calidad del producto de software es un concepto complejo que abarca varios aspectos como la funcionalidad, la usabilidad y la fiabilidad del software. En este sentido, ISO/IEC 25010 define una serie de criterios para evaluar la calidad del producto de software, como la precisión, la exactitud, el rendimiento y la capacidad de cumplir con requisitos.<br><br>Imagina que estás trabajando en un proyecto de desarrollo de software y necesitas asegurarte de que tu aplicación cumpla con ciertos estándares de calidad. La norma ISO/IEC 25010 te proporciona una guía para evaluar cómo se comporta tu producto frente a estos criterios, lo cual es fundamental para garantizar la satisfacción del cliente. ¿Cómo evaluarás la precisión en tu aplicación para garantizar su funcionalidad correcta? | ISO/IEC 25010 es un estándar de calidad del producto de software que describe las características y requisitos para la calidad del producto, incluyendo aspectos como la precisión, la completitud, el rendimiento y la usabilidad. Aunque se menciona en ISO 9001 como complemento, no es una norma independiente. Se recomienda consultar el texto oficial de ISO/IEC 29110 para obtener más información sobre cómo se relaciona con este estándar.<br><br>¿Cómo crees que las empresas pueden aplicar la calidad del producto descrita en ISO/IEC 25010 en su desarrollo de software? | ISO/IEC 25010 es un estándar que define las características y requisitos para la calidad del producto de software, estableciendo criterios para evaluar y mejorar la calidad del software. A diferencia de ISO 9001, que se centra en la gestión de calidad organizacional, ISO/IEC 25010 se enfoca específicamente en los aspectos técnicos y funcionales de la calidad del producto de software. ¿Qué características técnicas y funcionales de una aplicación de software se evaluarían según ISO/IEC 25010? |
| Palabras | 121 | 87 | 75 |
| Normas que nombra | ISO/IEC 25010 | ISO 9001, ISO/IEC 25010, ISO/IEC 29110 | ISO 9001, ISO/IEC 25010 |
| Normas/años sin respaldo en los documentos | ninguno | ninguno | ninguno |
| Ideas ancla que faltan | ninguna | ninguna | ninguna |
| Afirmaciones que los documentos contradicen | ninguna | ninguna | ninguna |
| Marca de analogía/situación | ✅ | ❌ | ❌ |

Similitud de texto entre pares (1 = idéntico; umbral de «distintas» < 0.8): novato~estandar = 0.07, novato~avanzado = 0.11, estandar~avanzado = 0.22. El avanzado cierra en pregunta: ✅; con marca socrática: ✅.

**Segunda vez, conversación nueva (caché):** novato: desde caché, estandar: desde caché, avanzado: generada, anonimo: desde caché. Recibió lo suyo: {novato: ✅, estandar: ✅, avanzado: ❌}; recibió la respuesta de otro estudiante: ninguno; el anónimo recibe lo del estándar: ✅.

## A3 · «¿Qué es ISO/IEC/IEEE 12207?» (tema 2.3)

| | **novato** | **estandar** | **avanzado** |
|---|---|---|---|
| Ajuste aplicado | `n=bajo|p=extensa|e=ejemplos` | `ninguno` | `n=alto|p=breve|e=comparativo` |
| Cita lo ya trabajado | — | — | 2.5, 2.2 |
| Respuesta | ISO/IEC 12207 es como un plan de trabajo para una empresa de construcción. Imagina que tienes un proyecto de software grande y complejo, con muchas personas trabajando en él. Necesitas saber qué procesos seguir, cómo organizar el trabajo y cuándo terminar cada fase. De manera similar, ISO/IEC 12207 define los procesos del ciclo de vida del software, como la planificación, el desarrollo, pruebas y mantenimiento. Estos procesos son como las etapas de una construcción: primero hay un diseño detallado, luego se comienza a construir, después se verifica que todo esté en orden y finalmente se entrega al cliente.<br><br>Pero ¿qué es lo que produce ISO/IEC 12207? Una descripción de arquitectura. Esto significa que el proceso define cómo debe ser la estructura del software, como las relaciones entre los diferentes componentes y cómo deben funcionar todos juntos. En otras palabras,ISO/IEC 42010: ¿Qué es lo que produce ISO/IEC 12207?<br><br>¿Cómo se relaciona TOGAF con ISO/IEC 42010? | ISO/IEC/IEEE 12207 es un estándar que define los procesos del ciclo de vida del software, estableciendo una estructura común para describir y gestionar las actividades involucradas en el desarrollo, implementación, pruebas y mantenimiento de sistemas de software. En particular, menciona la importancia de la "diseñada" arquitectura (es decir, según ISO/IEC 42010) como resultado del proceso de diseño de arquitectura definido por esta norma, que produce una descripción de arquitectura conforme a ISO/IEC/IEEE 42010. <br><br>¿Qué relación existe entre el proceso de "diseño de arquitectura" y la creación de un documento formal de la arquitectura de sistemas de software complejos? | ISO/IEC 12207 es un estándar que define los procesos del ciclo de vida del software y describe cómo se aplican en una organización. Se enfoca en la planificación, implementación y mantenimiento de proyectos de desarrollo de software. En otras palabras, trata sobre cómo gestionar el proceso de creación de software. ¿Qué implicaciones tiene ISO/IEC 12207 para el enfoque de planificación y gestión del proyecto de software? |
| Palabras | 154 | 98 | 66 |
| Normas que nombra | ISO/IEC 12207, ISO/IEC 42010 | ISO/IEC 42010, ISO/IEC/IEEE 12207, ISO/IEC/IEEE 42010 | ISO/IEC 12207 |
| Normas/años sin respaldo en los documentos | ninguno | ninguno | ninguno |
| Ideas ancla que faltan | ninguna | ninguna | ninguna |
| Afirmaciones que los documentos contradicen | ninguna | ninguna | ninguna |
| Marca de analogía/situación | ✅ | ❌ | ✅ |

Similitud de texto entre pares (1 = idéntico; umbral de «distintas» < 0.8): novato~estandar = 0.07, novato~avanzado = 0.11, estandar~avanzado = 0.21. El avanzado cierra en pregunta: ✅; con marca socrática: ❌.

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

# ISO/IEC 12207 — Procesos del Ciclo de Vida del Software 

## 1. Introducción y contexto 
ISO/IEC 12207 es la norma internacional que define un marco de referencia para los procesos del ciclo de 
vida del software, desde la concepción de un sistema hasta su retiro. No impone una metodología de 
desarrollo específica (no obliga a usar cascada, ágil o espiral), sino que describe qué procesos deben existir 
en un proyecto de software y qué actividades y tareas los componen, dejando a cada organización la 
libertad de decidir cómo ejecutarlos. 
Es una de las normas más relevantes para la Ingeniería de Software, ya que ofrece un lenguaje común 
entre clientes, proveedores, desarrolladores y gestores de proyecto.

## 2. Historia y evolución 
• Publicada por primera vez en 1995 por ISO/IEC, como resultado del trabajo conjunto de expertos 
internacionales en ingeniería de software. 
• Revisada en 2008, incorporando mejoras en la definición de procesos y alineándose mejor con 
ISO/IEC 15288 (procesos del ciclo de vida de sistemas). 
• La versión más reciente es ISO/IEC/IEEE 12207:2017, desarrollada conjuntamente con el IEEE, lo 
que refleja la convergencia entre normas de ingeniería de software de distintas organizaciones 
internacionales.

## 3. Objetivo y alcance 
El objetivo es proporcionar un marco de procesos común para adquirir, suministrar, desarrollar, operar, 
mantener y disponer productos y servicios de software, aplicable a organizaciones de cualquier tamaño y 
a proyectos de cualquier naturaleza (desarrollo interno, subcontratado, productos comerciales, sistemas 
embebidos, etc.).

## 4. Organismo emisor 
Desarrollada por el comité técnico conjunto ISO/IEC JTC 1, subcomité SC 7 (Ingeniería de software y 
sistemas), en colaboración con el IEEE Computer Society en su versión 2017.

## 5. Estructura general 
La norma organiza los procesos en varios grupos principales: 
1. Procesos de acuerdo: adquisición y suministro. 
2. Procesos de habilitación de proyecto de la organización: gestión del ciclo de vida, gestión de 
infraestructura, gestión de portafolio de proyectos, gestión de recursos humanos, gestión de 
calidad, gestión del conocimiento. 
3. Procesos de proyecto técnico: planificación, evaluación y control, gestión de decisiones, gestión 
de riesgos, gestión de configuración, gestión de la información, medición, aseguramiento de la 
calidad. 
4. Procesos técnicos: definición de necesidades, análisis de requisitos, diseño de arquitectura, diseño 
detallado, integración, verificación, transición, validación, operación, mantenimiento y disposición 
final. 
5. Procesos de implementación de software: análisis de requisitos de software, diseño de 
arquitectura de software, diseño detallado de software, construcción, integración y pruebas de 
software. 
6. Procesos de soporte de software: documentación, gestión de configuración de software, 
aseguramiento de calidad de software, verificación, validación, revisión, auditoría y resolución de 
problemas. 
7. Procesos de reutilización de software: gestión de dominio de reutilización, gestión de activos 
reutilizables, gestión de programas de reutilización.

## 6. Conceptos y terminología clave 
• Proceso: conjunto de actividades interrelacionadas que transforman entradas en salidas. 
• Actividad: conjunto de tareas dentro de un proceso. 
• Tarea: acción específica y concreta dentro de una actividad. 
• Ciclo de vida del software: evolución completa de un sistema de software, desde la concepción 
hasta el retiro. 
• Modelo de ciclo de vida: marco de referencia que organiza los procesos de forma temporal (por 
ejemplo, cascada, iterativo, ágil); ISO/IEC 12207 es independiente de cualquier modelo particular.

## 7. Principios fundamentales 
• Independencia de metodología: la norma no exige cascada ni ágil, adaptándose a ambos enfoques. 
• Escalabilidad: los procesos pueden adaptarse ("tailoring") según el tamaño y criticidad del 
proyecto. 
• Trazabilidad: se promueve la trazabilidad entre requisitos, diseño, implementación y pruebas. 
• Mejora continua de procesos, en línea con modelos de madurez como CMMI o ISO/IEC 33000 
(SPICE).

## 8. Procesos técnicos explicados (resumen conceptual) 
Análisis de requisitos 
Identifica y documenta las necesidades funcionales y no funcionales del software, sirviendo de base para 
el diseño posterior. 
Diseño de arquitectura 
Define la estructura de alto nivel del sistema: componentes, interfaces y relaciones entre ellos. 
Construcción (codificación) 
Traduce el diseño detallado en código fuente ejecutable, siguiendo estándares de codificación. 
Integración 
Combina los componentes de software desarrollados de forma independiente en un sistema funcional 
coherente. 
Verificación y validación 
La verificación confirma que el software se construyó correctamente según las especificaciones ("¿lo 
construimos bien?"); la validación confirma que el software satisface las necesidades reales del usuario 
("¿construimos lo correcto?"). 
Mantenimiento 
Cubre las modificaciones posteriores a la entrega: corrección de errores, mejoras, adaptaciones a nuevos 
entornos.

## 9. Proceso de adopción en una organización 
8. Seleccionar los procesos aplicables al contexto del proyecto (tailoring). 
9. Definir roles y responsables para cada proceso. 
10. Establecer métricas para evaluar la ejecución de los procesos. 
11. Documentar los procedimientos asociados a cada proceso. 
12. Ejecutar, monitorear y mejorar los procesos de forma iterativa.

## 10. Relación con otras normas 
• ISO/IEC 15288: procesos del ciclo de vida de sistemas (a nivel de sistema completo, no solo 
software); 12207 se considera su complemento específico para software. 
• ISO/IEC 25010: define los atributos de calidad que deben verificarse durante los procesos técnicos 
de 12207. 
• ISO/IEC 29110: perfil simplificado de procesos de ciclo de vida, basado parcialmente en 12207, 
para organizaciones pequeñas. 
• ISO/IEC 33000 (SPICE): permite evaluar el nivel de madurez de los procesos definidos según 
12207.

## 11. Aplicación práctica en informática 
• Uso como referencia para estructurar la documentación de proyectos de software académicos y 
profesionales. 
• Base conceptual para entender metodologías modernas (Scrum, DevOps) como formas 
particulares de ejecutar los procesos técnicos definidos por la norma. 
• Apoyo en la definición de contratos de desarrollo de software entre cliente y proveedor (procesos 
de acuerdo). 
• Referencia para diseñar planes de gestión de configuración y control de versiones.

## 12. Caso de aplicación ilustrativo 
Una empresa que desarrolla software a la medida para clientes externos utiliza ISO/IEC 12207 para 
estructurar sus contratos: define claramente los procesos de adquisición (qué entrega el cliente) y 
suministro (qué entrega la empresa desarrolladora), establece hitos de verificación y validación, y 
documenta el proceso de mantenimiento post-entrega, reduciendo ambigüedades contractuales y 
mejorando la trazabilidad del proyecto.

## 13. Preguntas de repaso 
• ¿Por qué se dice que ISO/IEC 12207 es independiente del modelo de ciclo de vida? 
• Explica la diferencia entre proceso, actividad y tarea según la norma. 
• ¿Cuál es la diferencia entre verificación y validación? 
• ¿Cómo se relaciona ISO/IEC 12207 con ISO/IEC 15288? 
• Menciona tres procesos de soporte de software y su propósito.

## 14. Glosario breve 
• Tailoring: adaptación de los procesos estándar a las necesidades específicas de un proyecto. 
• Gestión de configuración: control sistemático de los cambios en los artefactos de software. 
• Modelo de ciclo de vida: organización temporal de los procesos de desarrollo.

## 15. Para profundizar 
Se recomienda el texto oficial ISO/IEC/IEEE 12207:2017 disponible a través de ISO o IEEE, así como 
bibliografía académica de Ingeniería de Software que referencia esta norma (por ejemplo, Sommerville o 
Pressman).
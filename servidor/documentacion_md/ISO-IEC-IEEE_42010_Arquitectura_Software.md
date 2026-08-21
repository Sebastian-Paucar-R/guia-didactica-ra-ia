# ISO/IEC/IEEE 42010 — Descripción de la Arquitectura de Sistemas y Software 

## 1. Introducción y contexto 
ISO/IEC/IEEE 42010 es la norma internacional que establece cómo debe describirse formalmente la 
arquitectura de un sistema o de un software. No define una arquitectura concreta ni un estilo 
arquitectónico particular (como microservicios o arquitectura en capas), sino un marco conceptual y un 
conjunto de convenciones para documentar arquitecturas de forma consistente, comprensible y útil para 
las distintas partes interesadas de un proyecto. 
Para un estudiante de Informática que se especializa en arquitectura de software, esta norma es la 
referencia fundamental para entender qué información debe contener una "descripción de arquitectura" 
bien construida.

## 2. Historia y evolución 
• Su antecedente directo es el estándar IEEE 1471:2000, titulado "Recommended Practice for 
Architectural Description of Software-Intensive Systems", desarrollado por el IEEE. 
• En 2007, este estándar fue adoptado y armonizado internacionalmente como ISO/IEC 42010:2007, 
ampliando su alcance de "software" a "sistemas y software" en general. 
• Se revisó en 2011, dando lugar a ISO/IEC/IEEE 42010:2011, la versión más reconocida, que 
introdujo el concepto explícito de "interesados" (stakeholders), "inquietudes" (concerns), "puntos 
de vista" (viewpoints) y "vistas" (views) de forma más formalizada.

## 3. Objetivo y alcance 
El objetivo es establecer los requisitos que debe cumplir una descripción de arquitectura (Architecture 
Description, AD) para ser considerada completa y útil, independientemente del dominio (sistemas 
embebidos, sistemas empresariales, software distribuido) o del estilo arquitectónico empleado. Es 
aplicable a cualquier sistema, entendido en un sentido amplio (hardware, software, procesos, 
organizaciones).

## 4. Organismo emisor 
Es una norma desarrollada conjuntamente entre ISO/IEC JTC 1/SC 7 (Ingeniería de software y sistemas) y 
el IEEE, reflejando la convergencia de ambos organismos en normas clave de ingeniería de software.

## 5. Estructura general y conceptos centrales del marco conceptual 
La norma define un marco conceptual (conceptual framework) compuesto por entidades relacionadas 
entre sí: 
• Sistema (System): entidad de interés, cuya arquitectura se describe. 
• Arquitectura (Architecture): conceptos o propiedades fundamentales de un sistema en su 
entorno, encarnados en sus elementos, relaciones, y en los principios de su diseño y evolución. 
• Descripción de arquitectura (Architecture Description, AD): obra que documenta la arquitectura 
de un sistema. 
• Interesado (Stakeholder): individuo, equipo, organización o clase de ellos, con interés en un 
sistema. 
• Inquietud (Concern): interés en un sistema relevante para uno o más de sus interesados (por 
ejemplo, seguridad, rendimiento, mantenibilidad). 
• Punto de vista arquitectónico (Architecture Viewpoint): convención para construir un tipo de 
vista, que enmarca una o más inquietudes. 
• Vista arquitectónica (Architecture View): representación de un sistema completo desde la 
perspectiva de un conjunto relacionado de inquietudes. 
• Modelo de vista (View Model / Model Kind): convenciones para un tipo de modelización usado 
para construir una vista. 
• Correspondencia (Correspondence): relación que vincula dos o más elementos de arquitectura 
entre distintas vistas o modelos.

## 6. Relación entre los conceptos (resumen conceptual) 
El sistema tiene una arquitectura, que se documenta mediante una descripción de arquitectura. Esta 
descripción incluye una o más vistas, cada una construida siguiendo un punto de vista específico, que a su 
vez enmarca las inquietudes de determinados interesados. Este entramado formaliza el principio de que 
no existe una única vista "correcta" de una arquitectura, sino múltiples vistas complementarias, cada 
una útil para responder a distintas preguntas de distintos interesados (por ejemplo, un desarrollador se 
interesa en la vista de componentes y conectores, mientras que un gerente de operaciones se interesa en 
la vista de despliegue).

## 7. Principios fundamentales 
• Multiplicidad de vistas: una arquitectura compleja no puede describirse adecuadamente desde 
una única perspectiva. 
• Orientación a interesados: la documentación de arquitectura debe diseñarse pensando en quién 
la usará y para qué. 
• Reutilización de puntos de vista: los puntos de vista pueden definirse una vez y reutilizarse en 
distintos proyectos (por ejemplo, un punto de vista de seguridad estándar dentro de una 
organización). 
• Trazabilidad: las correspondencias permiten mantener la coherencia entre distintas vistas de una 
misma arquitectura. 
• Independencia de notación: la norma no impone un lenguaje de modelado específico (UML, 
ArchiMate, C4), siendo compatible con cualquiera de ellos.

## 8. Elementos adicionales del marco 
Decisión de arquitectura (Architecture Decision) 
Elección realizada durante el diseño de la arquitectura, junto con su justificación (racional), que puede 
documentarse formalmente mediante registros de decisión (Architecture Decision Records, ADR), una 
práctica ampliamente adoptada en la industria y compatible con este marco. 
Racional (Rationale) 
Explicación o justificación de las decisiones de diseño tomadas, incluyendo alternativas consideradas y 
descartadas. 
Marco de arquitectura (Architecture Framework) 
Convenciones, principios y prácticas para el análisis, diseño y documentación de arquitecturas dentro de 
un dominio de aplicación específico o comunidad de interesados (por ejemplo, TOGAF en el ámbito 
empresarial).

## 9. Proceso de elaboración de una descripción de arquitectura 
1. Identificar el sistema y sus interesados. 
2. Identificar las inquietudes relevantes de cada interesado. 
3. Seleccionar o definir los puntos de vista arquitectónicos que enmarcan esas inquietudes. 
4. Construir las vistas correspondientes, aplicando los modelos de vista definidos por cada punto de 
vista. 
5. Documentar las decisiones de arquitectura y su racional. 
6. Establecer correspondencias entre vistas para mantener la coherencia global. 
7. Revisar la descripción de arquitectura con los interesados para validar que cubre sus inquietudes.

## 10. Relación con otras normas 
• ISO/IEC 12207 e ISO/IEC 15288: el proceso de "diseño de arquitectura" definido en estas normas 
produce como resultado una descripción de arquitectura conforme a ISO/IEC/IEEE 42010. 
• TOGAF: marco de arquitectura empresarial (no una norma ISO) que puede considerarse un "marco 
de arquitectura" en el sentido definido por 42010, y que en muchos casos referencia 
explícitamente esta norma. 
• ISO/IEC 25010: las inquietudes de calidad (rendimiento, seguridad, mantenibilidad) documentadas 
en las vistas arquitectónicas suelen expresarse usando las características de este modelo de 
calidad. 
• UML y ArchiMate: lenguajes de modelado ampliamente usados como "modelos de vista" 
concretos dentro del marco conceptual de 42010.

## 11. Aplicación práctica en informática 
• Documentación formal de la arquitectura de sistemas de software complejos (por ejemplo, 
sistemas distribuidos o de microservicios). 
• Uso de Architecture Decision Records (ADR) como práctica ligera inspirada en los conceptos de 
esta norma, muy popular en equipos ágiles y DevOps. 
• Diseño de vistas específicas para distintos interesados en proyectos de gran escala: vista lógica 
para desarrolladores, vista de despliegue para operaciones, vista de seguridad para auditores. 
• Base conceptual para cursos universitarios de Arquitectura de Software.

## 12. Caso de aplicación ilustrativo 
El equipo de arquitectura de una plataforma de comercio electrónico identifica tres grupos de 
interesados: desarrolladores (interesados en la estructura de componentes y APIs), el equipo de 
operaciones (interesado en el despliegue y la escalabilidad) y los auditores de seguridad (interesados en 
el control de accesos y el cifrado de datos). Siguiendo el marco de ISO/IEC/IEEE 42010, define tres puntos 
de vista distintos y construye las vistas correspondientes, documentando además las decisiones clave de 
arquitectura, como la elección de una arquitectura de microservicios frente a un monolito, junto con su 
justificación.

## 13. Preguntas de repaso 
• ¿Cuál es la diferencia entre un "punto de vista" (viewpoint) y una "vista" (view) según la norma? 
• ¿Por qué la norma insiste en que no existe una única vista correcta de una arquitectura? 
• ¿Qué es una "inquietud" (concern) y qué relación tiene con los interesados de un sistema? 
• Explica qué es un Architecture Decision Record (ADR) y cómo se relaciona con el concepto de 
"racional" en la norma. 
• ¿Por qué se dice que ISO/IEC/IEEE 42010 es independiente de la notación de modelado utilizada?

## 14. Glosario breve 
• AD: Architecture Description, descripción de arquitectura. 
• Viewpoint: convención para construir un tipo de vista arquitectónica. 
• ADR: Architecture Decision Record, registro de decisión de arquitectura. 
• Racional: justificación documentada de una decisión de diseño.

## 15. Para profundizar 
Se recomienda consultar el texto oficial de ISO/IEC/IEEE 42010:2011 a través de los canales autorizados 
de ISO o IEEE, así como bibliografía especializada en arquitectura de software (por ejemplo, los trabajos 
de Bass, Clements y Kazman sobre "Software Architecture in Practice"). 
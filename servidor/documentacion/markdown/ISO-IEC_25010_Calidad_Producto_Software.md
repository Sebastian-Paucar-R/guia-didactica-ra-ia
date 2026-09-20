# ISO/IEC 25010 — Modelo de Calidad de Producto de Software (SQuaRE) 

## 1. Introducción y contexto 
ISO/IEC 25010 forma parte de la familia de normas SQuaRE (Software Product Quality Requirements and 
Evaluation — Requisitos y Evaluación de Calidad de Productos de Software), identificada como la serie 
ISO/IEC 25000. Específicamente, ISO/IEC 25010 define el modelo de calidad que se usa como referencia 
para especificar, medir y evaluar la calidad de un producto de software y de un sistema informático en su 
conjunto. 
Para un estudiante de Informática, esta norma es esencial porque responde a una pregunta central de la 
Ingeniería de Software: ¿qué significa que un software sea "de calidad"? La norma descompone ese 
concepto abstracto en características medibles.

## 2. Historia y evolución 
• Antes de 2011, el modelo de calidad de referencia era ISO/IEC 9126, publicada en partes entre 
2001 y 2004, que definía seis características de calidad. 
• En 2011 se publicó ISO/IEC 25010:2011, reemplazando a ISO/IEC 9126 dentro del nuevo marco 
SQuaRE, ampliando el modelo a ocho características y separando la calidad "en uso" de la calidad 
"del producto". 
• Fue revisada y republicada como ISO/IEC 25010:2023, que refinó las características y añadió una 
nueva dimensión ("seguridad" reforzada y ajustes en "compatibilidad" y "flexibilidad").

## 3. Objetivo y alcance 
El objetivo es proporcionar un modelo de calidad estandarizado, común y comparable, que sirva de base 
para: especificar requisitos de calidad de software, definir criterios de evaluación, comparar productos de 
software, y guiar actividades de aseguramiento de calidad durante el desarrollo.

## 4. Organismo emisor 
Desarrollada por el subcomité SC 7 (Ingeniería de software y sistemas) del comité técnico conjunto 
ISO/IEC JTC 1, dentro de la serie SQuaRE (ISO/IEC 2501n a 2504n).

## 5. Estructura general 
La norma define dos modelos complementarios: 
1. Modelo de calidad del producto: aplicable a las propiedades estáticas y dinámicas del software. 
2. Modelo de calidad en uso: aplicable a la experiencia del usuario final al utilizar el producto en un 
contexto real.

## 6. Características del modelo de calidad de producto 
• Adecuación funcional: grado en que el software provee funciones que satisfacen las necesidades 
declaradas e implícitas (completitud, corrección, pertinencia funcional). 
• Eficiencia de desempeño: comportamiento relativo a los recursos utilizados (tiempo de respuesta, 
uso de recursos, capacidad). 
• Compatibilidad: capacidad de intercambiar información y coexistir con otros sistemas 
(interoperabilidad, coexistencia). 
• Usabilidad: facilidad con la que los usuarios pueden operar el software (reconocibilidad, 
aprendizaje, operabilidad, accesibilidad). 
• Fiabilidad (confiabilidad): capacidad de mantener un nivel de desempeño bajo condiciones 
específicas (madurez, disponibilidad, tolerancia a fallos, recuperabilidad). 
• Seguridad: capacidad de proteger información y datos (confidencialidad, integridad, no repudio, 
responsabilidad, autenticidad, resistencia). 
• Mantenibilidad: facilidad con la que el software puede modificarse (modularidad, reusabilidad, 
analizabilidad, capacidad de modificación, capacidad de prueba). 
• Portabilidad: facilidad con la que el software puede transferirse de un entorno a otro 
(adaptabilidad, capacidad de instalación, capacidad de reemplazo).

## 7. Características del modelo de calidad en uso 
• Efectividad: precisión y completitud con la que los usuarios logran sus objetivos. 
• Eficiencia: recursos utilizados en relación con la efectividad lograda. 
• Satisfacción: grado en que se cumplen las necesidades del usuario (utilidad, confianza, placer, 
comodidad). 
• Libertad de riesgo: mitigación de riesgos potenciales para la economía, vida humana, salud o el 
medio ambiente. 
• Cobertura de contexto: capacidad de uso efectivo en contextos especificados y en contextos más 
allá de los inicialmente previstos.

## 8. Conceptos y terminología clave 
• Característica de calidad: categoría de atributos de calidad del software relevante para un 
conjunto de necesidades. 
• Subcaracterística: subdivisión de una característica que agrupa atributos relacionados. 
• Métrica de calidad: medida cuantitativa del grado en que un producto posee una característica 
dada. 
• Calidad en uso: perspectiva de la calidad desde el punto de vista del usuario final en un contexto 
de uso real.

## 9. Proceso de aplicación práctica 
3. Identificar los stakeholders y sus necesidades de calidad. 
4. Seleccionar las características y subcaracterísticas relevantes para el proyecto. 
5. Definir métricas específicas para cada subcaracterística seleccionada (por ejemplo, tiempo medio 
entre fallos para "madurez"). 
6. Establecer niveles objetivo (targets) de calidad, normalmente en la especificación de requisitos no 
funcionales.
7. Evaluar el producto durante y después del desarrollo, comparando resultados frente a los 
objetivos definidos.

## 10. Relación con otras normas 
• ISO/IEC 25012: modelo de calidad de datos, complementario al modelo de calidad de producto. 
• ISO/IEC 25040: proceso de evaluación de calidad de producto de software (parte del marco 
SQuaRE). 
• ISO/IEC 25041: guía de evaluación para desarrolladores, adquirentes y evaluadores 
independientes. 
• ISO/IEC 12207: los procesos técnicos de esta norma (verificación, validación) usan el modelo de 
ISO/IEC 25010 como criterio de calidad. 
• ISO/IEC 29119: normas de pruebas de software que operacionalizan la verificación de varias 
características de ISO/IEC 25010.

## 11. Aplicación práctica en informática 
• Definición de requisitos no funcionales en documentos de especificación de software. 
• Diseño de casos de prueba orientados a características específicas (rendimiento, seguridad, 
usabilidad).
• Evaluación comparativa de productos de software o frameworks antes de su adopción. 
• Base para checklist de revisión de código relacionados con mantenibilidad (modularidad, 
complejidad ciclomática).

## 12. Caso de aplicación ilustrativo 
Un equipo que desarrolla una aplicación móvil bancaria utiliza ISO/IEC 25010 para estructurar sus 
requisitos no funcionales: define objetivos de "fiabilidad" (disponibilidad del 99.9%), "seguridad" (cifrado 
de extremo a extremo y autenticación biométrica), y "usabilidad" (tiempo máximo de tres pasos para 
completar una transferencia). Estos objetivos se convierten en criterios de aceptación verificables durante 
las pruebas.

## 13. Preguntas de repaso 
• ¿Cuál es la diferencia entre el modelo de calidad de producto y el modelo de calidad en uso? 
• Menciona las ocho características del modelo de calidad de producto y da un ejemplo de cada una. 
• ¿Qué diferencia hay entre una característica y una subcaracterística de calidad? 
• ¿Por qué ISO/IEC 25010 reemplazó a ISO/IEC 9126?
• ¿Cómo se relaciona esta norma con el proceso de verificación y validación de ISO/IEC 12207?

## 14. Glosario breve 
• SQuaRE: familia de normas ISO/IEC 25000 sobre requisitos y evaluación de calidad de software. 
• Requisito no funcional: requisito que especifica criterios de calidad más que funciones concretas. 
• Métrica: medida cuantificable asociada a una característica de calidad.

## 15. Para profundizar 
Se recomienda revisar el texto oficial de ISO/IEC 25010:2023 y las normas complementarias de la serie 
SQuaRE a través de los canales oficiales de ISO, así como bibliografía de ingeniería de requisitos y 
aseguramiento de calidad de software. 
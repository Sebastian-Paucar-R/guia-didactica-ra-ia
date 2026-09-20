# ISO/IEC 33000 — Evaluación de Procesos de Software (SPICE) 

## 1. Introducción y contexto 
ISO/IEC 33000 es la familia de normas internacionales dedicada a la evaluación y mejora de la capacidad 
de los procesos dentro de una organización, con especial aplicación histórica en la ingeniería de software 
y de sistemas. Es la evolución directa del proyecto conocido como SPICE (Software Process Improvement 
and Capability Determination), que originalmente se publicó como ISO/IEC 15504. 
Mientras que normas como ISO/IEC 12207 definen qué procesos deben existir en el ciclo de vida del 
software, ISO/IEC 33000 responde a una pregunta distinta: ¿qué tan bien (con qué nivel de madurez o 
capacidad) se ejecutan esos procesos?

## 2. Historia y evolución 
• El proyecto SPICE comenzó a inicios de los años noventa como una iniciativa internacional para 
desarrollar un estándar de evaluación de procesos de software, en parte inspirado por el modelo 
CMM (Capability Maturity Model) desarrollado por el Software Engineering Institute (SEI) en 
Estados Unidos. 
• Se publicó formalmente como ISO/IEC 15504 en varias partes entre 2003 y 2006. 
• A partir de 2013, el marco fue reestructurado y renombrado como la familia ISO/IEC 33000, 
generalizando su aplicación más allá del software, hacia la evaluación de procesos de cualquier 
tipo de organización.

## 3. Objetivo y alcance 
El objetivo es proporcionar un marco estandarizado para evaluar la capacidad de los procesos de una 
organización, permitiendo: identificar fortalezas y debilidades de los procesos actuales, comparar la 
capacidad de procesos entre distintas organizaciones o proyectos, y guiar iniciativas de mejora de 
procesos de forma objetiva y basada en evidencia.

## 4. Organismo emisor 
Desarrollada por el subcomité SC 7 (Ingeniería de software y sistemas) del comité técnico conjunto 
ISO/IEC JTC 1, en colaboración con el grupo internacional que originalmente impulsó el proyecto SPICE.

## 5. Estructura general de la familia ISO/IEC 33000 
La familia se organiza en varias partes, entre las más relevantes: 
• ISO/IEC 33001: conceptos y terminología. 
• ISO/IEC 33002: requisitos para realizar una evaluación de procesos. 
• ISO/IEC 33003: requisitos para las medidas de capacidad de procesos. 
• ISO/IEC 33004: requisitos para modelos de procesos y modelos de evaluación de procesos. 
• ISO/IEC 33020: modelo de medición de la capacidad de procesos (define los niveles de capacidad). 
• ISO/IEC 33063: modelo de evaluación de procesos específico para VSE, compatible con ISO/IEC 
29110. 
• ISO/IEC TS 33053 y modelos asociados: modelos de referencia de procesos derivados de ISO/IEC 
12207.

## 6. Conceptos y terminología clave 
• Capacidad de proceso: caracterización de la habilidad de un proceso para cumplir sus objetivos 
actuales o proyectados. 
• Nivel de capacidad: escala que caracteriza la capacidad de un proceso, desde el nivel 0 
(incompleto) hasta el nivel 5 (en optimización). 
• Atributo de proceso: característica medible de la capacidad de un proceso, aplicable a cualquier 
proceso. 
• Modelo de referencia de procesos (PRM): conjunto de definiciones de procesos, típicamente 
derivado de una norma como ISO/IEC 12207. 
• Modelo de evaluación de procesos (PAM): modelo que operacionaliza el PRM en indicadores 
evaluables.

## 7. Los seis niveles de capacidad de procesos 
• Nivel 0 — Incompleto: el proceso no se implementa o no logra sus objetivos. 
• Nivel 1 — Ejecutado: el proceso implementado logra su propósito. 
• Nivel 2 — Gestionado: el proceso ejecutado se planifica, monitorea y ajusta, y sus productos de 
trabajo se establecen, controlan y mantienen adecuadamente. 
• Nivel 3 — Establecido: el proceso gestionado se implementa usando un proceso estándar definido, 
capaz de lograr sus resultados. 
• Nivel 4 — Predecible: el proceso establecido opera dentro de límites definidos que permiten 
lograr sus resultados esperados, usando técnicas cuantitativas. 
• Nivel 5 — En optimización: el proceso predecible se mejora continuamente para cumplir con 
objetivos de negocio relevantes actuales y futuros. 
Cada nivel (a partir del nivel 2) se compone de uno o más atributos de proceso, evaluados en una escala 
de cumplimiento (N: No logrado, P: Parcialmente logrado, L: Ampliamente logrado, F: Totalmente 
logrado).

## 8. Principios fundamentales 
• Objetividad y evidencia: las evaluaciones se basan en evidencia documental y observable, no en 
percepciones subjetivas. 
• Independencia del modelo de proceso evaluado: el marco de medición de capacidad (ISO/IEC 
33020) puede aplicarse sobre distintos modelos de referencia de procesos (no solo ISO/IEC 12207). 
• Mejora orientada a objetivos de negocio: el propósito último no es alcanzar un nivel de madurez 
por sí mismo, sino mejorar el desempeño real de la organización. 
• Escalabilidad: aplicable tanto a grandes organizaciones como, mediante perfiles específicos, a VSE 
(ISO/IEC 33063, compatible con ISO/IEC 29110).

## 9. Proceso de evaluación de procesos 
1. Planificación de la evaluación: definir el propósito, alcance (qué procesos y unidades organizativas 
se evaluarán) y restricciones. 
2. Recolección de datos: mediante entrevistas, revisión de documentación y observación directa de 
la ejecución de los procesos. 
3. Validación de datos: asegurar que la evidencia recolectada sea suficiente, objetiva y confiable. 
4. Calificación de atributos de proceso: asignar el nivel de cumplimiento (N, P, L, F) a cada atributo 
evaluado. 
5. Determinación del nivel de capacidad: consolidar los resultados para determinar el nivel de 
capacidad alcanzado por cada proceso evaluado. 
6. Elaboración de reportes: documentar los resultados y recomendaciones de mejora.

## 10. Relación con otras normas 
• ISO/IEC 12207: modelo de referencia de procesos más utilizado como base para las evaluaciones 
SPICE en el ámbito del software. 
• ISO/IEC 15288: modelo de referencia de procesos de sistemas, también evaluable bajo el marco 
33000. 
• ISO/IEC 29110: cuenta con un modelo de evaluación de procesos compatible (ISO/IEC 33063) 
adaptado a organizaciones pequeñas. 
• CMMI: modelo de madurez de procesos alternativo desarrollado por el SEI (Carnegie Mellon), 
conceptualmente similar pero con metodología, escalas y proceso de certificación distintos; 
frecuentemente comparado con SPICE en el ámbito académico. 
• Automotive SPICE: adaptación sectorial de ISO/IEC 33000 ampliamente utilizada en la industria 
automotriz para evaluar proveedores de software embebido.

## 11. Aplicación práctica en informática 
• Evaluación y mejora de procesos de desarrollo de software en empresas de TI. 
• Selección de proveedores de software mediante la exigencia de un nivel mínimo de capacidad de 
procesos (frecuente en la industria automotriz con Automotive SPICE). 
• Diagnóstico de madurez organizacional antes de iniciar iniciativas de transformación digital o 
adopción de metodologías ágiles a escala. 
• Base metodológica para investigaciones académicas sobre mejora de procesos de software.

## 12. Caso de aplicación ilustrativo 
Una empresa proveedora de software para la industria automotriz debe demostrar a sus clientes que sus 
procesos de desarrollo alcanzan al menos el nivel de capacidad 2 según Automotive SPICE (basado en 
ISO/IEC 33000). Un equipo evaluador externo recolecta evidencia sobre los procesos de gestión de 
requisitos e implementación de software, calificando los atributos de proceso correspondientes y 
determinando que el proceso de gestión de requisitos alcanza el nivel 2, mientras que el proceso de 
pruebas se mantiene en nivel 1, generando un plan de mejora específico para este último.

## 13. Preguntas de repaso 
• ¿Cuál es la diferencia conceptual entre un modelo de referencia de procesos (PRM) y un modelo 
de evaluación de procesos (PAM)? 
• Describe brevemente los seis niveles de capacidad de procesos. 
• ¿En qué se diferencia ISO/IEC 33000 de ISO/IEC 12207? 
• ¿Qué es Automotive SPICE y cómo se relaciona con ISO/IEC 33000? 
• ¿Por qué la objetividad y la evidencia son principios fundamentales en una evaluación de 
procesos?

## 14. Glosario breve 
• PRM: Process Reference Model, modelo de referencia de procesos. 
• PAM: Process Assessment Model, modelo de evaluación de procesos. 
• Atributo de proceso: característica medible usada para determinar el nivel de capacidad.

## 15. Para profundizar 
Se recomienda consultar el texto oficial de la familia ISO/IEC 33000, especialmente ISO/IEC 33001, 33002 
y 33020, a través de los canales autorizados de ISO, así como literatura académica sobre modelos de 
madurez de procesos de software (SPICE y CMMI). 
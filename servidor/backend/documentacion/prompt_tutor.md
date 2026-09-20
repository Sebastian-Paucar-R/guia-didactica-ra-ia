# Prompt del tutor: intención, memoria y respuestas mejor calibradas

Código: `app/services/tutor_service.py` (prompts y utilidades), `app/services/memoria_service.py` (memoria),
orquestado en `RAGService.get_answer` (`app/services/rag_service.py`). Batería de prueba:
`scripts/bateria_tutor.py`; respuestas completas de la última corrida:
[`bateria_tutor_resultados.md`](bateria_tutor_resultados.md).

## Qué hace

| Requisito | Cómo se cumple |
|---|---|
| Respuesta directa, breve, sin preámbulo | `PROMPT_TUTOR` prohíbe preámbulos; `limpiar_preambulo` quita "excelente pregunta", "claro,", "hola, ¿cómo estás?", "entiendo que…", "lo siento, pero…" si el LLM los pone igual. Modo PUNTUAL: 2-3 oraciones, sin listas |
| Intención → nivel | `detectar_intencion`: PUNTUAL (cierra con una pregunta de reflexión), PROFUNDIZAR (varios párrafos + ejemplo de desarrollo de software), TAREA (pasos numerados con pistas, nunca resuelta) |
| Tutor inviolable | Regla fija del prompt + modo TAREA + reintento si la guía no trae ≥3 pasos numerados o queda en <45 palabras (negativa seca) |
| Solo contexto; si no alcanza, decirlo | Ver "Términos sin respaldo" y "Verificación de citas" abajo |
| Tono / sin estructura fija | Prosa natural; lista numerada solo en TAREA (lo pide el propio requisito: "descomponerla en pasos") |
| Memoria por `conversation_id` | `MemoriaConversacional` (RAM). Los seguimientos se reescriben como pregunta autónoma para recuperar y filtrar |
| Citar norma + documento | Fragmentos etiquetados `[Documento: nombre — «título»]`; el recordatorio final pide nombrar el documento fuente |

`tipo` nuevo: `sin_contexto` (el tema está en el sílabo pero no en los documentos). Los `tipo` posibles:
`saludo | funcionamiento | sin_documentos | respuesta | sin_contexto | redireccion | error`.

### Intención (por qué no es solo un LLM)
El clasificador por LLM de `llama3.2` (3B) marcó como PROFUNDIZAR casi toda pregunta conceptual (75 % de aciertos en
28 frases; 64 % con un prompt "más inclusivo" que a cambio no detectaba TAREA). Por eso el orden es:
1. Señales explícitas (`resuélveme`, `hazlo por mí`, `respuesta completa` → TAREA; `explícame mejor`, `no entendí`,
   `ejemplo`, `amplía`… → PROFUNDIZAR). TAREA gana a PROFUNDIZAR ("redáctame un ejemplo de informe").
2. Pregunta directa autocontenida (qué es, cuál es la diferencia, cuándo aplica, cuántas…) → PUNTUAL, sin LLM.
3. Solo lo demás (imperativos sin señal, mensajes con "eso") → llamada corta al LLM; ante la duda, PUNTUAL.

### Memoria
Se guardan 8 turnos por conversación (4 se muestran al LLM, respuestas recortadas a 450 caracteres), máx. 200
conversaciones (LRU), **en RAM**: se pierde al reiniciar el servidor. Si el cliente no manda `conversation_id`, el
servidor crea uno y lo devuelve; la página de prueba (`localStorage`) y la pantalla de chat de Flutter lo guardan y
reenvían. "Limpiar historial" en la página crea una conversación nueva.
La reescritura de seguimientos solo se aplica si el mensaje depende de la conversación (referencias "eso/lo anterior",
petición de profundizar, ≤3 palabras): con el LLM reescribiendo siempre, "¿Qué es un SGSI?" salía convertida en
"¿Qué es un SGSI? ¿Es un tipo de ciclo PDCA? …". Además se conserva solo la primera pregunta generada.

### Términos sin respaldo (regla 5)
Un aviso dentro del prompt ("si el contexto no trata el tema, dilo") no bastó: con Scrum el modelo lo explicó de
memoria y lo atribuyó a "ISO/IEC 25010". Ahora `terminos_sin_respaldo` detecta lo que el estudiante nombra y no está en
el contexto ni en los nombres de documentos: números de norma (`29119`), siglas (`CMMI`, `DORA`, `CI/CD`), mayúscula
mixta (`DevOps`) y nombres propios del sílabo (`Scrum`, `Kanban`). Si falta alguno, otro prompt (`PROMPT_SIN_CONTEXTO`)
dice que no está en los documentos y da la **ubicación real** en el sílabo (`ubicar_en_silabo`: Scrum → Unidad 1,
29119 → Unidad 4). Se probó antes un "juez" LLM (¿el contexto responde la pregunta?): 13/20 de aciertos, descartado.

### Verificación de citas (reglas 5 y 7)
Tras generar, se comprueba contra el contexto recuperado (+ conversación + títulos de unidades): identificadores
`ISO/IEC/IEEE nnnnn`, años (`:2015`), `cláusula N`, conteos ("11 claves de control", "7 cláusulas"; los números escritos
con letras respaldan cifras: "diez" ↔ 10) y siglas/nombres del sílabo. Si algo no está respaldado se reintenta una vez
avisando al LLM y, si insiste, se eliminan esas oraciones. También: se quita la etiqueta `[Documento: …]` pegada
literalmente, se recorta una oración cortada por el límite de tokens y se elimina un encabezado final vacío
("Referencias:").

### Ollama
`num_ctx=8192` en todas las instancias (con el 2048 por defecto el prompt se truncaba por el principio; si difiere
entre instancias Ollama recarga el modelo), `num_predict=1024` y `repeat_penalty=1.15` en la respuesta: sin tope, una
respuesta llegó a **3 846 palabras en bucle** (67 s). Temperatura 0.35.

## Batería y resultados

Seis preguntas de los tres tipos de intención (más dos extra para las reglas 5 y 7 y una de tema sin documento), cada
conversación con su `conversation_id` para que los seguimientos prueben la memoria. Última corrida (v8, servidor real,
`llama3.2`):

| # | Pregunta (resumen) | Intención | Detectada | `tipo` | Palabras |
|---|---|---|---|---|---|
| A1 | ¿Qué es la mejora continua en la ISO 9001? | PUNTUAL | PUNTUAL | respuesta | 64 |
| A2 | No entendí, ¿me lo explicas mejor con un ejemplo? | PROFUNDIZAR | PROFUNDIZAR | respuesta | 230 |
| B1 | Diferencia entre ISO/IEC 27001 e ISO/IEC 27002 | PUNTUAL | PUNTUAL | respuesta | 75 |
| B2 | Amplía eso de los controles, no me quedó claro | PROFUNDIZAR | PROFUNDIZAR | respuesta | 324 |
| C | Resuélveme este ejercicio: riesgos de mi app de delivery + matriz completa (ISO 31000) | TAREA | TAREA | respuesta | 281 |
| D | Redáctame el plan de auditoría interna de calidad, dame todo resuelto | TAREA | TAREA | respuesta | 266 |
| E | ¿Qué dice la ISO/IEC/IEEE 29119 sobre los niveles de prueba? (no está en la base) | PUNTUAL | PUNTUAL | sin_contexto | 58 |
| F | ¿Cuántas cláusulas tiene la ISO 9001 y qué exige la cláusula 8? | PUNTUAL | PUNTUAL | respuesta | 71 |
| G | ¿Qué es Scrum y cuáles son sus roles? (sílabo, sin documento) | PUNTUAL | PUNTUAL | sin_contexto | 82 |

Intención 9/9. La memoria funcionó: en A2 y B2 el mensaje ("¿me lo explicas mejor…?", "amplía eso de los controles") se
reescribió con el tema de la respuesta anterior. C y D entregaron 5 pasos con pistas y una invitación a hacer el paso 1,
sin la matriz ni el plan terminados.

### Historial de ajustes (batería v1 → v8)
- **v1**: 3 de 4 preguntas puntuales clasificadas como PROFUNDIZAR (respuestas de 217-329 palabras); "Amplía eso de los
  controles" reescrita a otro tema y con una lista inventada de "11 categorías"; sobre ISO 29119 (no está en la base)
  el modelo inventó "cuatro niveles de prueba"; tarea D respondió en 19 palabras.
- **v2**: intención por reglas → puntuales de 45-94 palabras. Aparece la generación desbocada (3 846 palabras) y una
  negativa seca ("No puedo cumplir con esa solicitud"). Scrum se atribuyó a ISO/IEC 25010 (el propio prompt traía ese
  ejemplo: se eliminó).
- **v3-v5**: recordatorio del modo al final del prompt, tope de tokens, pregunta de reflexión generada, ruta
  `sin_contexto` por términos ausentes, pasos numerados en TAREA, ubicación real en el sílabo.
- **v6-v7**: verificador de citas más estricto (contexto, no la lista de documentos), reintentos de TAREA, limpieza de
  preámbulos y encabezados colgados. Un defecto propio: el verificador de conteos eliminaba "10 cláusulas" (correcto)
  porque los documentos escriben "diez" → se aceptan números en letras.
- **v8**: resultado de arriba.

## Defectos que siguen (limitaciones de llama3.2 3B, no del pipeline)
- **F**: dice "La ISO 9001 tiene 7 cláusulas" (los documentos dicen diez). El verificador solo detecta números que no
  aparecen en el contexto; "7" sí aparece como numeración de otra cosa. Las respuestas varían entre corridas (en v3-v5
  dijo 10).
- **Citar el documento** (regla 7) es irregular: D nombra documentos, A1/B1/F casi nunca. El identificador completo
  sí aparece cuando se cita una norma.
- **E** mezcla el título de la Unidad 2 con el número de la Unidad 4 y sugiere "leer la norma 29119" (fuente externa,
  aceptable); en versiones previas recomendó un documento que no trata el tema.
- **G** llama "documento" a la unidad del sílabo.
- La pregunta de reflexión generada a veces no encaja del todo (A1 habla de "una pregunta anterior" que no existe).
- Ejemplos de PROFUNDIZAR pueden traer detalles inventados (p. ej. pasos de implementación de un control) que un
  verificador léxico no distingue de información del contexto.
- La latencia depende de la máquina: a mitad de la sesión Ollama pasó a ~17 tokens/s (medido con una llamada directa)
  y las respuestas, que en v3 tardaban 1-6 s, pasaron a 7-45 s (hasta 85 s en una tarea con reintentos).

Mejoras posibles: un modelo mayor para redactar (la mayoría de los defectos son de este modelo), reranking de los
fragmentos recuperados, embeddings multilingües y una verificación semántica de las afirmaciones contra el contexto.

# Adaptación al estudiante: lectura crítica de la evaluación real

Escrito a mano. `evaluacion_adaptacion.md` (generado por `pruebas/evaluar_adaptacion.py`) es la ronda oficial con sus verdictos
automáticos; **estos verdictos son heurísticos y se equivocaron en las dos primeras corridas** (dijeron «contenido normativo ✅» con
respuestas que inventaban o trasladaban datos). Este documento recoge lo que se vio al leer las respuestas, cómo evolucionó el ajuste
y qué se puede y qué no se puede afirmar. Modelo: `llama3.2` (3B) en Ollama, embeddings `all-MiniLM-L6-v2`, 3 preguntas
(ISO 9001, ISO/IEC 25010, ISO/IEC/IEEE 12207) × 3 estudiantes (novato: nivel bajo + extensa + ejemplos; estándar: perfil inicial;
avanzado: nivel alto + breve + comparativo) por ronda, servidor y bases limpios en cada ronda.

## Qué hace el ajuste y qué no (medido)

| Por perfil | Primera versión (6 resp.) | Final (9 resp.) |
|---|---|---|
| Palabras (media): novato / estándar / avanzado | 138 / 70 / 66 | 156 / 80 / 70 |
| Novato abre con una analogía o situación | 0 de 6 | 9 de 9 |
| Avanzado cierra con un «por qué» / «qué pasaría si…» | 0 de 6 | 4 de 9 |
| Caché: recibió la respuesta de otro estudiante | ninguno | ninguno (9 de 9 preguntas) |
| Segunda vez, conversación nueva: novato / estándar / anónimo / avanzado | — | desde caché / desde caché / desde caché / generada (es personal: cita lo ya trabajado) |

- **Se logra**: respuestas de distinta longitud y forma (similitud de texto entre pares ≤ 0,46; casi siempre < 0,25), analogías para el
  nivel bajo, contraste con otra norma para el estilo comparativo, cierres más exigentes para el nivel alto, y un caché que nunca
  mezcla segmentos.
- **No se logra con este modelo**: la *breve* apenas acorta (66–70 palabras frente a 70–80 del perfil inicial; el modo puntual ya era
  corto); el cierre socrático llega en menos de la mitad de las respuestas; y **el contenido normativo no coincide de forma fiable
  entre perfiles** (siguiente sección).

## El contenido normativo NO coincide siempre (lectura de la ronda oficial final)

| Pregunta | Novato (extensa + ejemplos) | Estándar (sin ajuste) | Avanzado (breve + comparativo) |
|---|---|---|---|
| ISO 9001 | ❌ dice que la norma «aborda la seguridad de la información y el gobierno de riesgos» y lo ilustra con ISO 27001: inventado | ✅ correcta (certificación por organismos acreditados) | ✅ correcta y breve |
| ISO/IEC 25010 | ⚠️ relleno («precisión, exactitud») | ❌ «no es una norma independiente… consulta ISO/IEC 29110»: falso | ✅ contraste correcto con ISO 9001 |
| ISO/IEC/IEEE 12207 | ❌ atribuye a 12207 lo que es de 42010, texto incoherente al final («En otras palabras,ISO/IEC 42010: ¿Qué es lo que produce…?») y pregunta de cierre sobre TOGAF | ⚠️ texto torpe («la "diseñada" arquitectura») | ✅ correcta, genérica |

- Los verdictos automáticos de esa ronda salieron ✅ en las tres preguntas. **Ninguna comprobación automática detecta esto**: no hay
  número, norma o año inventado; son atributos trasladados de un documento a otro y relleno.
- Lo que muestran las rondas: el perfil **extenso** (respuestas de 120–200 palabras) es el que más se aleja de los
  documentos, porque el modelo pequeño rellena con lo que ya tiene en el contexto (otros documentos de la misma consulta). El
  **avanzado** (corto) es el más fiel. El **estándar** también falla: no es un problema exclusivo del perfil.
- **Contaminación previa al perfil**: en ISO 9001 el modelo, con o sin ajuste, a veces le atribuye a ISO 9001 lo que el documento
  dice de ISO 31000 («norma de directrices, no certificable»; el documento dice lo contrario de ISO 9001). En una serie de tres
  rondas apareció en 2 de 3 respuestas del estándar y 2 de 3 del avanzado, y en ninguna del novato.

## Historial de iteraciones

1. **Primera corrida** (`evaluacion_adaptacion_corrida1.md`). Encontró: (a) el filtro redirigió como «fuera de tema» los seguimientos
   «Sigo sin entender, explícamelo otra vez» y «Dame otro ejemplo» (el reformulador LLM los dio por autosuficientes) y el perfil
   descartó esas señales; (b) el filtro ubicó «Muéstrame un ejemplo con un equipo pequeño» en mantenimiento (Unidad 4) y el perfil lo
   anotó como tema consultado (error del perfil); (c) el novato inventó «tres niveles de madurez… madera, pino, roble» para ISO/IEC/IEEE
   12207 y el avanzado le atribuyó a ISO 9001 «no certificable».
2. **Correcciones**: un seguimiento sigue en el tema anterior salvo que nombre otro por palabras clave; las directivas de analogía y de
   contraste dicen que no arrastran datos ni rasgos de otra norma; el modo extenso dice «explica solo con el CONTEXTO»;
   `tutor_service._CONTEO` verifica también cantidades en letras («tres niveles»); el banco lleva ahora una lista `prohibido`
   (regex de afirmaciones que los documentos contradicen) — una lista de fallos ya vistos, no una garantía.
3. **Segunda serie**: la forma casi no cambiaba (analogías 0 de 6, cierres exigentes 0 de 6): un modelo pequeño no obedece una
   instrucción enterrada en un prompt largo. Se repite el ajuste en el recordatorio final (`Adaptacion.recordatorio`) y la pregunta de
   cierre se regenera con un prompt enfocado y la exigencia del nivel (`tutor.ajustar_pregunta_final`, verificada como el resto de
   citas). Además: la cláusula de cierre no va en las tareas (chocaba con «invita a hacer el paso 1»).
4. **Tercera serie y final**: un seguimiento corto, sin tema propio, que el filtro redirige justo después de una explicación cuenta
   como señal (`es_seguimiento_puro`); en cinco ejecuciones reales de la evolución el filtro redirigió por error 3 de 25 seguimientos.
   Ronda oficial final: evolución completa ✅ (nivel 3,0 → 2,6 → 2,2 sin saltos, dificultad marcada tras «No entendí», estilo a
   «ejemplos» al tercer pedido, la siguiente respuesta ya se adapta).

## Otros defectos previos al perfil que se vieron

- `tutor_service.terminos_sin_respaldo` busca los nombres del sílabo como **subcadena** del texto normalizado: «Dame» (de «Dame otro
  ejemplo») coincide con «fun**dame**ntos» y el seguimiento sale como `sin_contexto` («"Dame" no aparece en los documentos»). No se ha
  tocado (no es del perfil); conviene buscar por palabra completa.
- El reformulador (`reformular_pregunta`) devuelve el mensaje sin cambios cuando el LLM lo da por autosuficiente y entonces el filtro
  lo juzga sin contexto; la redirección de seguimientos legítimos es un fallo del flujo previo.

## Qué se puede y qué no se puede afirmar

- Se puede: el mecanismo funciona (perfil persistente, cambios graduales solo por conducta observable, directiva con invariantes de
  rigor, verificaciones de salida aplicadas igual, caché segmentado sin cruces, endpoints) y produce respuestas de forma distinta.
- No se puede: que el contenido normativo sea el mismo para todos con `llama3.2`. Con 3 preguntas y 3 rondas no hay tasas fiables;
  los números de arriba son una muestra, no una medición.
- Antes de exponerlo a estudiantes: probar con un modelo mayor (misma batería), limitar la longitud de la respuesta extensa o
  desactivarla, y añadir una comprobación de atribución por oración (¿cada afirmación está en el fragmento del documento citado?).
  El perfil solo actúa si el cliente envía `user_id`, y hoy ni la página de prueba ni Flutter lo envían.

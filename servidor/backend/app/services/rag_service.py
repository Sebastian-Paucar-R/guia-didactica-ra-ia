import hashlib
import re
import shutil
import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import settings
from app.core.silabo import texto_silabo, ubicar_en_silabo
from app.services import pertinencia_service as pertinencia
from app.services import tutor_service as tutor
from app.services.conversion_service import decodificar_texto
from app.services.memoria_service import MemoriaConversacional

COLECCION = "langchain"
_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")

ESTADO_INDEXADO = "indexado"
ESTADO_OMITIDO = "omitido_sin_cambios"
ESTADO_ERROR = "error"


class RAGService:
    """RAG sobre documentacion/markdown/ con índice Chroma incremental.

    Cada chunk lleva metadata {nombre_archivo, hash, fecha_indexado}. El hash es el
    SHA-256 del contenido del .md y los ids de los chunks son f"{hash}:{n}", así que
    un mismo contenido nunca puede duplicarse en la colección.
    """

    def __init__(self, embeddings=None, persist_dir=None, docs_dir=None,
                 sincronizar_al_iniciar: bool = True, llm=None,
                 llm_clasificador=None, llm_redireccion=None, llm_reformulador=None, memoria=None):
        self._lock = threading.RLock()
        self.persist_dir = Path(persist_dir or settings.BASE_VECTORIAL_DIR)
        self.markdown_dir = (Path(docs_dir) / "markdown") if docs_dir else settings.MARKDOWN_DIR
        self.embeddings = embeddings or HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        # Mismo num_ctx en todas las instancias: si difiere, Ollama recarga el modelo en cada cambio,
        # y con el valor por defecto (2048) el prompt del tutor se truncaría por el principio.
        ctx = settings.NUM_CTX
        self.llm = llm or ChatOllama(
            model=settings.MODELO_LLM, temperature=0.35, num_ctx=ctx,
            num_predict=settings.MAX_TOKENS_RESPUESTA, repeat_penalty=settings.REPEAT_PENALTY)
        # Llamadas cortas y deterministas: clasificación DENTRO/FUERA (una palabra) y selección de
        # temas relacionados para la redirección (hasta 3 números)
        self.llm_clasificador = llm_clasificador or ChatOllama(
            model=settings.MODELO_LLM, temperature=0, num_predict=16, num_ctx=ctx)
        # Redirección: temperatura alta para que la redacción varíe entre respuestas
        self.llm_redireccion = llm_redireccion or ChatOllama(
            model=settings.MODELO_LLM, temperature=0.9, num_ctx=ctx, num_predict=400)
        # Reescritura de seguimientos como pregunta autónoma: determinista y corta
        self.llm_reformulador = llm_reformulador or ChatOllama(
            model=settings.MODELO_LLM, temperature=0, num_predict=80, num_ctx=ctx)
        self.memoria = memoria or MemoriaConversacional(
            max_turnos=settings.MEMORIA_MAX_TURNOS, max_conversaciones=settings.MEMORIA_MAX_CONVERSACIONES)
        self.splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        self._abrir_vectorstore()
        if sincronizar_al_iniciar:
            self.sincronizar()

    # ------------------------------------------------------------------
    # Índice
    # ------------------------------------------------------------------

    def _abrir_vectorstore(self):
        # Coseno: la distancia de Chroma es 1 - similitud, lo que da un score 0-1 interpretable
        # para el filtro de pertinencia (con la métrica por defecto, L2, el rango depende del modelo).
        self.vectorstore = Chroma(
            collection_name=COLECCION,
            embedding_function=self.embeddings,
            persist_directory=str(self.persist_dir),
            collection_configuration={"hnsw": {"space": "cosine"}},
        )
        self.retriever = self.vectorstore.as_retriever(search_kwargs={"k": 4})

    def _espacio_distancia(self) -> str | None:
        try:
            return (self.vectorstore._collection.configuration.get("hnsw") or {}).get("space")
        except Exception:
            return None

    def contar_chunks(self) -> int:
        return self.vectorstore._collection.count()

    @staticmethod
    def calcular_hash(datos: bytes) -> str:
        return hashlib.sha256(datos).hexdigest()

    def indexar_archivo(self, md_path: Path) -> tuple[str, int]:
        """Indexa un .md de forma incremental. Devuelve (estado, chunks_indexados)."""
        md_path = Path(md_path)
        with self._lock:
            datos = md_path.read_bytes()
            hash_actual = self.calcular_hash(datos)
            nombre = md_path.name

            previos = self.vectorstore.get(where={"nombre_archivo": nombre}, include=["metadatas"])
            ids_obsoletos = [
                i for i, m in zip(previos["ids"], previos["metadatas"])
                if (m or {}).get("hash") != hash_actual
            ]

            if self.vectorstore.get(where={"hash": hash_actual}, limit=1)["ids"]:
                # Contenido ya indexado: no se toca; solo se retiran versiones viejas del mismo nombre.
                if ids_obsoletos:
                    self.vectorstore.delete(ids=ids_obsoletos)
                return ESTADO_OMITIDO, 0

            fragmentos = self.splitter.split_text(decodificar_texto(datos))
            if not fragmentos:
                raise ValueError("el documento está vacío")

            fecha = datetime.now(timezone.utc).isoformat(timespec="seconds")
            documentos = [
                Document(
                    page_content=texto,
                    metadata={
                        "nombre_archivo": nombre,
                        "hash": hash_actual,
                        "fecha_indexado": fecha,
                        "source": nombre,
                        "chunk": n,
                    },
                )
                for n, texto in enumerate(fragmentos)
            ]
            # Primero se agregan los nuevos (upsert por id) y luego se eliminan los anteriores:
            # si algo falla al embeber, la versión previa sigue disponible.
            self.vectorstore.add_documents(
                documentos, ids=[f"{hash_actual}:{n}" for n in range(len(documentos))]
            )
            if ids_obsoletos:
                self.vectorstore.delete(ids=ids_obsoletos)
            return ESTADO_INDEXADO, len(documentos)

    def _archivos_markdown(self) -> list[Path]:
        return sorted(self.markdown_dir.glob("*.md")) if self.markdown_dir.exists() else []

    def _indexar_todos(self) -> list[dict]:
        resultados = []
        for md in self._archivos_markdown():
            try:
                estado, chunks = self.indexar_archivo(md)
                resultados.append({"nombre": md.name, "estado": estado, "chunks": chunks})
            except Exception as e:
                print(f"[RAG] Error al indexar {md.name}: {e}")
                resultados.append({"nombre": md.name, "estado": ESTADO_ERROR, "chunks": 0, "detalle": str(e)})
        return resultados

    def sincronizar(self) -> dict:
        """Puesta al día incremental (arranque): indexa lo nuevo/cambiado y poda lo borrado.

        Si el store es anterior a este esquema (chunks sin `hash`, con duplicados de los
        arranques antiguos), se reconstruye por completo una única vez.
        """
        with self._lock:
            self._limpiar_segmentos_huerfanos()
            existentes = self.vectorstore.get(include=["metadatas"])
            if any(not (m or {}).get("hash") for m in existentes["metadatas"]):
                print("[RAG] Store con esquema anterior detectado: reconstruyendo una vez.")
                return self.reconstruir()
            if self._espacio_distancia() != "cosine":
                print("[RAG] Store con métrica de distancia distinta de coseno: reconstruyendo una vez.")
                return self.reconstruir()

            en_disco = {p.name for p in self._archivos_markdown()}
            huerfanos = [
                i for i, m in zip(existentes["ids"], existentes["metadatas"])
                if m.get("nombre_archivo") not in en_disco
            ]
            if huerfanos:
                self.vectorstore.delete(ids=huerfanos)
                print(f"[RAG] Podados {len(huerfanos)} chunks de documentos ya inexistentes.")

            resultados = self._indexar_todos()
            print(f"[RAG] Sincronizado: {len(resultados)} documentos, {self.contar_chunks()} chunks.")
            return {"documentos": len(resultados), "chunks": self.contar_chunks(), "resultados": resultados}

    def _limpiar_segmentos_huerfanos(self) -> None:
        """delete_collection deja en disco la carpeta del segmento vectorial anterior
        (una por reconstrucción); se eliminan las que ya no figuran en chroma.sqlite3.
        En Windows el segmento recién descartado sigue bloqueado hasta que termina el proceso,
        así que es de mejor esfuerzo: se reintenta en cada arranque (`sincronizar`)."""
        db = self.persist_dir / "chroma.sqlite3"
        if not db.exists():
            return
        try:
            con = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)
            try:
                vivos = {fila[0] for fila in con.execute("SELECT id FROM segments")}
            finally:
                con.close()
        except sqlite3.Error:
            return
        for carpeta in self.persist_dir.iterdir():
            if carpeta.is_dir() and _UUID.fullmatch(carpeta.name) and carpeta.name not in vivos:
                shutil.rmtree(carpeta, ignore_errors=True)

    def reconstruir(self) -> dict:
        """Mantenimiento: descarta la colección completa y reindexa todo markdown/."""
        with self._lock:
            inicio = time.perf_counter()
            try:
                self.vectorstore.delete_collection()
            except Exception as e:
                print(f"[RAG] delete_collection: {e}")
            self._abrir_vectorstore()
            resultados = self._indexar_todos()
            self._limpiar_segmentos_huerfanos()
            total = self.contar_chunks()
            print(f"[RAG] Reconstruido: {len(resultados)} documentos, {total} chunks.")
            return {
                "documentos": len(resultados),
                "chunks": total,
                "resultados": resultados,
                "duracion_s": round(time.perf_counter() - inicio, 2),
            }

    def resumen_indice(self) -> dict:
        """Chunks por documento indexado (para la interfaz)."""
        with self._lock:
            datos = self.vectorstore.get(include=["metadatas"])
        por_archivo: dict[str, dict] = {}
        for m in datos["metadatas"]:
            entrada = por_archivo.setdefault(
                m["nombre_archivo"], {"nombre_archivo": m["nombre_archivo"], "chunks": 0,
                                      "hash": m.get("hash"), "fecha_indexado": m.get("fecha_indexado")}
            )
            entrada["chunks"] += 1
        return {"total_chunks": len(datos["ids"]),
                "documentos": sorted(por_archivo.values(), key=lambda d: d["nombre_archivo"])}

    # ------------------------------------------------------------------
    # Consulta
    # ------------------------------------------------------------------

    def buscar_con_score(self, pregunta: str, k: int = 4) -> list[tuple[Document, float]]:
        """Top-k fragmentos con su similitud coseno (0-1, mayor = más parecido)."""
        resultados = self.vectorstore.similarity_search_with_score(pregunta, k=k)
        return [(doc, 1.0 - distancia) for doc, distancia in resultados]

    def get_answer(self, question: str, conversation_id: str | None = None) -> dict:
        """Devuelve {response, context, tipo}.

        tipo: saludo | funcionamiento | sin_documentos | respuesta | sin_contexto | redireccion | error
        Con `conversation_id` el tutor recuerda los turnos anteriores de esa conversación
        (memoria en RAM): los seguimientos ("explícame eso mejor") se reescriben como pregunta
        autónoma antes de recuperar y filtrar.
        """
        turnos = self.memoria.obtener(conversation_id, ultimos=settings.MEMORIA_TURNOS_PROMPT)
        resultado = self._procesar(question, turnos)
        if resultado["tipo"] in ("respuesta", "funcionamiento", "redireccion", "sin_contexto"):
            self.memoria.agregar(conversation_id, question, resultado["response"], resultado["tipo"])
        return resultado

    def _procesar(self, question: str, turnos: list) -> dict:
        """Flujo completo. Filtro de pertinencia (orden): 1) excepciones (saludo, preguntas sobre el
        tutor); 2) score de similitud de los fragmentos vs UMBRAL_PERTINENCIA; 3) si ninguno lo supera,
        el LLM confirma DENTRO/FUERA del temario. FUERA => redirección, sin responder el contenido."""
        question_lower = question.lower().strip()

        # Único mensaje predefinido
        if question_lower in ["hola", "buenas", "buenos días", "buenas tardes", "hey", "hi", "hoola"]:
            return {
                "response": (
                    "¡Hola! Soy tu Tutor IA especializado en normativas de Ingeniería de Software. "
                    "¿Sobre qué norma o concepto te gustaría que te oriente hoy?"
                ),
                "context": "",
                "tipo": "saludo",
            }

        filtro = settings.FILTRO_PERTINENCIA_ACTIVO
        if filtro and pertinencia.es_pregunta_sobre_tutor(question):
            _log_filtro("funcionamiento", question)
            return self._responder_sobre_tutor(question)

        if self.contar_chunks() == 0:
            return {
                "response": "Aún no hay documentos cargados. Por favor, agrega material en la carpeta de documentación.",
                "context": "",
                "tipo": "sin_documentos",
            }

        # Seguimientos: la recuperación y el filtro trabajan con la pregunta ya autónoma
        autonoma = tutor.reformular_pregunta(self.llm_reformulador, question, turnos)
        resultados = self.buscar_con_score(autonoma)
        mejor = max((score for _, score in resultados), default=0.0)

        if filtro and mejor < settings.UMBRAL_PERTINENCIA:
            # Candidata a fuera de tema: el LLM confirma con una llamada corta
            try:
                veredicto = pertinencia.clasificar_pertinencia(self.llm_clasificador, autonoma)
            except Exception as e:
                print(f"[FILTRO] Falló la clasificación ({type(e).__name__}); se responde con el RAG.")
                veredicto = None
            if veredicto is None:
                veredicto = pertinencia.DENTRO  # ante la duda no se bloquea al estudiante
            _log_filtro("candidata", autonoma, mejor, veredicto)

            if veredicto == pertinencia.FUERA:
                try:
                    texto = pertinencia.generar_redireccion(
                        self.llm_redireccion, autonoma, llm_seleccion=self.llm_clasificador)
                except Exception as e:
                    return {"response": f"Ocurrió un error al generar la respuesta: {str(e)}",
                            "context": "", "tipo": "error"}
                return {"response": texto, "context": "", "tipo": "redireccion"}
        else:
            _log_filtro("pertinente", autonoma, mejor)

        intencion = tutor.detectar_intencion(self.llm_clasificador, question)
        if intencion == tutor.PROFUNDIZAR:
            # Más material para desarrollar; con historial se ancla también en la pregunta previa del
            # estudiante, para que una reescritura imprecisa no desvíe la recuperación del tema.
            consulta = f"{turnos[-1].pregunta} {autonoma}" if turnos else autonoma
            resultados = self.buscar_con_score(consulta, k=6)
        _log_tutor(intencion, question, autonoma)
        mejor = max((score for _, score in resultados), default=0.0)
        return self._responder_con_contexto(question, autonoma, [d for d, _ in resultados], turnos, intencion, mejor)

    def _titulo_documento(self, nombre_archivo: str) -> str:
        """Título del documento (primera línea del .md), p. ej. 'ISO/IEC 25010 — Modelo de Calidad…'."""
        try:
            with open(self.markdown_dir / nombre_archivo, encoding="utf-8") as f:
                return f.readline().lstrip("#").strip()
        except OSError:
            return ""

    def _generar_respuesta(self, variables: dict) -> str:
        texto = (tutor.PROMPT_TUTOR | self.llm | StrOutputParser()).invoke(variables)
        texto = tutor.limpiar_etiquetas_documento(texto)
        return tutor.recortar_a_oracion_completa(
            tutor.quitar_encabezado_colgado(tutor.limpiar_preambulo(texto)))

    def _responder_con_contexto(self, question: str, autonoma: str, docs: list[Document],
                                turnos: list, intencion: str = tutor.PUNTUAL, mejor_score: float = 1.0) -> dict:
        fragmentos = []
        for doc in docs:
            nombre = doc.metadata.get("nombre_archivo", "")
            fragmentos.append((nombre, self._titulo_documento(nombre), doc.page_content))
        contexto = tutor.formatear_contexto(fragmentos)
        documentos = [d["nombre_archivo"].removesuffix(".md") for d in self.resumen_indice()["documentos"]]
        historial = tutor.formatear_historial(turnos)
        # Documentos de los que salió el contexto, para que el tutor los nombre al citar
        fuentes = "; ".join(dict.fromkeys(f"«{titulo or nombre.removesuffix('.md')}»"
                                          for nombre, titulo, _ in fragmentos[:3])) or "ninguno"

        variables = {
            "modo": tutor.INSTRUCCIONES_MODO.get(intencion, tutor.INSTRUCCIONES_MODO[tutor.PUNTUAL]),
            "recordatorio": tutor.RECORDATORIOS.get(intencion, tutor.RECORDATORIOS[tutor.PUNTUAL])
            + tutor.RECORDATORIO_CITAS.format(fuentes=fuentes),
            "documentos": ", ".join(documentos) or "(ninguno)",
            "silabo": texto_silabo(),
            "historial": historial,
            "contexto": contexto,
            "pregunta": question,
            "aclaracion": f"\n(Se refiere a: {autonoma})" if autonoma != question else "",
        }
        # Términos que el estudiante nombra y no aparecen en la base (Scrum, ISO 29119, CI/CD...): no hay
        # respaldo para explicarlos. Con un modelo pequeño un aviso dentro del prompt no basta (los explica
        # de memoria y los atribuye a un documento cualquiera), así que se usa un prompt específico.
        faltantes = tutor.terminos_sin_respaldo(
            f"{question} {autonoma}", contexto + " " + " ".join(documentos), texto_silabo())
        if faltantes:
            print(f"[TUTOR] Sin respaldo en los documentos: {faltantes}".encode("ascii", "backslashreplace").decode())
            try:
                ubicacion = list(dict.fromkeys(u for f in faltantes for u in ubicar_en_silabo(f)))
                texto = tutor.generar_sin_contexto(
                    self.llm, question, faltantes, documentos, texto_silabo(), contexto, ubicacion)
                return {"response": texto, "context": contexto[:1000], "tipo": "sin_contexto"}
            except Exception as e:
                return {"response": f"Ocurrió un error al generar la respuesta: {str(e)}",
                        "context": "", "tipo": "error"}

        if mejor_score < settings.UMBRAL_RESPALDO:
            # Aunque la pregunta sea del temario, los documentos pueden no cubrirla (p. ej. Scrum): sin este
            # aviso el modelo pequeño la explica de memoria y la atribuye a un documento cualquiera.
            variables["aclaracion"] += (
                "\nAVISO: la búsqueda no encontró en los documentos material claramente relacionado con esta "
                "pregunta (similitud baja). Si el CONTEXTO no trata el tema, dilo con claridad, no lo describas de "
                "memoria ni lo atribuyas a un documento, y sugiere la unidad del sílabo o el documento donde buscarlo.")

        # Lo que respalda una cita: el contexto recuperado (con los títulos de sus documentos), la conversación
        # y los títulos de las unidades del sílabo. No cuentan la lista completa de documentos ni los temas del
        # sílabo: un LLM pequeño cita normas o técnicas "relacionadas" que no salen del contexto.
        respaldo = " ".join([contexto, historial, question, autonoma, texto_silabo(con_temas=False)])

        def sin_respaldo(texto: str) -> list[str]:
            return list(dict.fromkeys(tutor.normas_no_respaldadas(texto, respaldo)
                                      + tutor.terminos_sin_respaldo(texto, respaldo, texto_silabo())))

        tipo = "respuesta"
        try:
            response = self._generar_respuesta(variables)
            invalidas = sin_respaldo(response)
            if invalidas:
                # El LLM citó normas/cláusulas que no están en el contexto: se reintenta una vez
                # avisándole y, si insiste, se eliminan esas oraciones.
                print(f"[TUTOR] Citas sin respaldo en el contexto: {invalidas}; se reintenta.")
                variables["aclaracion"] += (
                    f"\nATENCIÓN: en un borrador mencionaste {', '.join(invalidas)}, que NO aparece en el "
                    "contexto. No lo menciones; usa solo las normas y cláusulas del contexto.")
                response = self._generar_respuesta(variables)
                response = tutor.quitar_oraciones_con(response, sin_respaldo(response))
            for _ in range(2):
                if not (intencion == tutor.TAREA and (len(response.split()) < 45 or tutor.numero_de_pasos(response) < 3)):
                    break
                # Negativa seca, demasiado corta o sin pasos: se pide una guía por pasos (hasta 2 reintentos)
                print("[TUTOR] Respuesta a la tarea sin pasos o demasiado corta; se reintenta pidiendo pasos guiados.")
                if "tu borrador fue demasiado corto" not in variables["aclaracion"]:
                    variables["aclaracion"] += (
                        "\nATENCIÓN: tu borrador fue demasiado corto o se negó. No te niegues: ayuda al estudiante "
                        "con una lista numerada de 4 o 5 pasos concretos (1., 2., 3., ...), cada uno con una pista "
                        "o pregunta guía, e invítalo a hacer el primer paso.")
                mejor_respuesta = self._generar_respuesta(variables)
                if tutor.numero_de_pasos(mejor_respuesta) > tutor.numero_de_pasos(response):
                    response = mejor_respuesta
            if intencion == tutor.PUNTUAL:
                response = tutor.terminar_con_pregunta(self.llm, response)
        except Exception as e:
            response = f"Ocurrió un error al generar la respuesta: {str(e)}"
            tipo = "error"

        return {
            "response": response,
            "context": contexto[:1000],
            "tipo": tipo,
        }

    def _responder_sobre_tutor(self, question: str) -> dict:
        """Preguntas sobre el propio tutor: se responde con datos reales (documentos cargados y
        temario), no con un texto fijo."""
        documentos = [
            d["nombre_archivo"].removesuffix(".md").replace("_", " ")
            for d in self.resumen_indice()["documentos"]
        ]
        prompt = ChatPromptTemplate.from_template("""
Eres un tutor universitario de la asignatura "Normativas de Ingeniería de Software". Un estudiante te pregunta por tu funcionamiento (qué puedes hacer, qué documentos tienes, en qué temas puedes ayudarlo). Responde de forma natural y conversacional usando únicamente la información de abajo; no inventes capacidades.

Qué haces: respondes preguntas sobre normativas de ingeniería de software basándote únicamente en los documentos cargados; explicas conceptos y orientas al estudiante; si algo no está en los documentos, lo dices con honestidad. Recuerdas los mensajes anteriores de la misma conversación, así que el estudiante puede pedirte que amplíes o aclares algo que ya dijiste.

Documentos cargados actualmente:
{documentos}

Temario de la asignatura (algunos temas pueden no tener aún un documento cargado):
{silabo}

Pregunta del estudiante:
{question}

Respuesta:
""")
        try:
            response = (prompt | self.llm | StrOutputParser()).invoke({
                "documentos": "\n".join(f"- {d}" for d in documentos) or "(ninguno todavía)",
                "silabo": texto_silabo(con_temas=False),
                "question": question,
            })
            tipo = "funcionamiento"
        except Exception as e:
            response, tipo = f"Ocurrió un error al generar la respuesta: {str(e)}", "error"
        return {"response": response, "context": "", "tipo": tipo}


def _log_filtro(decision: str, pregunta: str, score: float | None = None, veredicto: str | None = None) -> None:
    """Traza de cada decisión del filtro (para medir redirecciones y ajustar el umbral)."""
    partes = [f"decision={decision}"]
    if score is not None:
        partes.append(f"score={score:.3f} umbral={settings.UMBRAL_PERTINENCIA}")
    if veredicto:
        partes.append(f"llm={veredicto}")
    linea = f"[FILTRO] {' '.join(partes)} pregunta={pregunta.strip()[:120]!r}"
    print(linea.encode("ascii", "backslashreplace").decode("ascii"))  # seguro con consolas cp1252


def _log_tutor(intencion: str, pregunta: str, autonoma: str) -> None:
    extra = f" reformulada={autonoma.strip()[:120]!r}" if autonoma != pregunta else ""
    linea = f"[TUTOR] intencion={intencion} pregunta={pregunta.strip()[:120]!r}{extra}"
    print(linea.encode("ascii", "backslashreplace").decode("ascii"))


_instancia: RAGService | None = None
_lock_instancia = threading.Lock()


def get_rag_service() -> RAGService:
    """Instancia única compartida (main.py y los endpoints): evita indexar dos veces al arrancar."""
    global _instancia
    with _lock_instancia:
        if _instancia is None:
            _instancia = RAGService()
        return _instancia

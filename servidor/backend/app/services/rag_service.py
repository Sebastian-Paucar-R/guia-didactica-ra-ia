import os
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser


class RAGService:
    def __init__(self):
        self.vectorstore = None
        self.retriever = None
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        self.llm = ChatOllama(model="llama3.2", temperature=0.4)
        self.load_documentacion()

    def load_documentacion(self):
        """Versión de depuración - fuerza la ruta correcta"""
        
        # RUTA FORZADA (ajusta solo si es necesario)
        docs_path = r"C:\Users\Sebas\PROYECTO\servidor\documentacion"
        
        print("=" * 60)
        print(f"Ruta forzada de documentos: {docs_path}")
        print(f"¿Existe la carpeta?: {os.path.exists(docs_path)}")
        
        if not os.path.exists(docs_path):
            print("ERROR: La carpeta no existe.")
            return

        archivos = os.listdir(docs_path)
        print(f"Archivos detectados ({len(archivos)}):")
        for f in archivos:
            print(f"  - {f}")
        print("=" * 60)

        documents = []

        for filename in archivos:
            file_path = os.path.join(docs_path, filename)

            if not os.path.isfile(file_path):
                continue

            try:
                if filename.lower().endswith(".pdf"):
                    loader = PyPDFLoader(file_path)
                    docs = loader.load()
                    documents.extend(docs)
                    print(f"✓ PDF cargado: {filename} ({len(docs)} páginas)")

                elif filename.lower().endswith((".md", ".txt")):
                    loader = TextLoader(file_path, encoding="utf-8")
                    docs = loader.load()
                    documents.extend(docs)
                    print(f"✓ Texto cargado: {filename}")

                else:
                    print(f"• Ignorado (extensión no soportada): {filename}")

            except Exception as e:
                print(f"✗ Error al cargar {filename}: {e}")

        print("=" * 60)
        print(f"Total de documentos cargados: {len(documents)}")

        if not documents:
            print("⚠️  No se pudo cargar ningún documento. Revisa los archivos.")
            return

        # Dividir en fragmentos
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        splits = text_splitter.split_documents(documents)

        # Guardar base vectorial
        persist_path = r"C:\Users\Sebas\PROYECTO\servidor\base_vectorial"
        
        self.vectorstore = Chroma.from_documents(
            documents=splits,
            embedding=self.embeddings,
            persist_directory=persist_path
        )
        self.retriever = self.vectorstore.as_retriever(search_kwargs={"k": 4})

        print(f"✅ RAG cargado exitosamente con {len(splits)} fragmentos.")
        print("=" * 60)

    def get_answer(self, question: str) -> dict:
        question_lower = question.lower().strip()

        # Único mensaje predefinido
        if question_lower in ["hola", "buenas", "buenos días", "buenas tardes", "hey", "hi", "hoola"]:
            return {
                "response": (
                    "¡Hola! Soy tu Tutor IA especializado en normativas de Ingeniería de Software. "
                    "¿Sobre qué norma o concepto te gustaría que te oriente hoy?"
                ),
                "context": ""
            }

        if not self.retriever:
            return {
                "response": "Aún no hay documentos cargados. Por favor, agrega material en la carpeta de documentación.",
                "context": ""
            }

        docs = self.retriever.invoke(question)
        context = "\n\n".join([doc.page_content for doc in docs[:4]]) if docs else ""

        prompt = ChatPromptTemplate.from_template("""
Eres un tutor universitario experto en normativas de Ingeniería de Software 
(ISO 9001, ISO/IEC 25010, ISO/IEC 27001, ISO/IEC 12207, etc.).

Instrucciones:
- Responde de forma natural, clara y conversacional.
- Utiliza únicamente la información del contexto proporcionado.
- Adapta tu respuesta al nivel de la pregunta del estudiante.
- Puedes explicar, dar ejemplos, hacer preguntas de reflexión o profundizar según sea necesario.
- No sigas un guion ni una secuencia de pasos predefinidos.
- Si el contexto no contiene información suficiente, indícalo de forma honesta.

Contexto de las normativas:
{context}

Pregunta del estudiante:
{question}

Respuesta:
""")

        chain = prompt | self.llm | StrOutputParser()

        try:
            response = chain.invoke({
                "context": context if context else "No se encontró información relevante en los documentos.",
                "question": question
            })
        except Exception as e:
            response = f"Ocurrió un error al generar la respuesta: {str(e)}"

        return {
            "response": response,
            "context": context[:1000] if context else ""
        }
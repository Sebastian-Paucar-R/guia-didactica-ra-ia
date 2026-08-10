import os
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings


class RAGService:
    def __init__(self):
        self.vectorstore = None
        self.retriever = None
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        self.load_documentacion()

    def load_documentacion(self):
        """Carga los documentos PDF de la carpeta documentacion"""
        if not os.path.exists("documentacion"):
            print("⚠️  Carpeta 'documentacion' no encontrada. Creándola...")
            os.makedirs("documentacion", exist_ok=True)
            return

        loader = PyPDFDirectoryLoader("documentacion")
        documents = loader.load()

        if not documents:
            print("⚠️  No se encontraron documentos PDF en documentacion")
            return

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        splits = text_splitter.split_documents(documents)

        self.vectorstore = Chroma.from_documents(
            documents=splits,
            embedding=self.embeddings,
            persist_directory="base_vectorial"
        )
        self.retriever = self.vectorstore.as_retriever(search_kwargs={"k": 4})

        print(f"✅ RAG cargado exitosamente con {len(splits)} fragmentos de documentos.")

    def get_answer(self, question: str) -> dict:
        """
        Devuelve un diccionario con:
        - response: texto limpio para el usuario
        - context: texto técnico completo (opcional)
        """
        if not self.retriever:
            return {
                "response": "El sistema aún no tiene documentos cargados. Agrega PDFs en la carpeta 'documentacion'.",
                "context": ""
            }

        question_lower = question.lower().strip()

        # Saludos
        if question_lower in ["hola", "buenas", "buenos días", "buenas tardes", "hey", "hi", "hoola"]:
            return {
                "response": (
                    "¡Hola! Soy tu Tutor IA especializado en normativas de Ingeniería de Software.\n\n"
                    "Puedo ayudarte a comprender normas como ISO/IEC 25010, ISO 9001, ISO/IEC 27001 y otras.\n\n"
                    "¿Sobre qué normativa o concepto te gustaría que te guíe hoy?"
                ),
                "context": ""
            }

        if any(word in question_lower for word in ["gracias", "ok", "entendido", "vale"]):
            return {
                "response": "¡De nada! Si tienes otra duda sobre las normativas, estoy aquí para orientarte.",
                "context": ""
            }

        # Búsqueda en documentos
        docs = self.retriever.invoke(question)

        if not docs:
            return {
                "response": (
                    "No encontré información suficiente en los documentos cargados.\n\n"
                    "Intenta reformular la pregunta o especifica la norma (ISO 25010, ISO 9001, etc.)."
                ),
                "context": ""
            }

        context = "\n\n".join([doc.page_content for doc in docs[:3]])

        # Respuesta limpia para el usuario
        clean_response = (
            "He encontrado información relevante en las normativas cargadas.\n\n"
            "¿Qué parte te genera más dudas? Puedo darte pistas, ejemplos o orientarte paso a paso "
            "sin entregarte la respuesta completa."
        )

        return {
            "response": clean_response,
            "context": context[:1200]
        }
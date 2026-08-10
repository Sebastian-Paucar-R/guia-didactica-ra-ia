from fastapi import APIRouter
from pydantic import BaseModel
from app.services.rag_service import RAGService

router = APIRouter()
rag_service = RAGService()


class ChatRequest(BaseModel):
    message: str
    user_id: str | None = None


class ChatResponse(BaseModel):
    response: str
    context: str = ""
    status: str = "success"


@router.post("/chat", response_model=ChatResponse)
async def chat_with_tutor(request: ChatRequest):
    print(f"\n[USUARIO] → {request.message}")

    result = rag_service.get_answer(request.message)

    # result es un diccionario: {"response": "...", "context": "..."}
    response_text = result.get("response", "Sin respuesta")
    context_text = result.get("context", "")

    print(f"[TUTOR] → {response_text[:250]}...\n")

    return ChatResponse(
        response=response_text,
        context=context_text,
        status="success"
    )
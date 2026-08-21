from fastapi import APIRouter
from pydantic import BaseModel
from app.services.rag_service import RAGService

router = APIRouter()

# Instancia única
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
    
    return ChatResponse(
        response=result.get("response", "Sin respuesta"),
        context=result.get("context", ""),
        status="success"
    )
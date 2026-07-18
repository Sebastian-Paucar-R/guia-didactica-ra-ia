from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    user_id: str | None = None

class ChatResponse(BaseModel):
    response: str
    status: str = "success"

@router.post("/chat", response_model=ChatResponse)
async def chat_with_tutor(request: ChatRequest):
    user_message = request.message.strip()
    
    response_text = "¡Hola! Soy tu tutor IA. ¿En qué normativas de Ingeniería de Software necesitas ayuda?"
    
    return ChatResponse(response=response_text)
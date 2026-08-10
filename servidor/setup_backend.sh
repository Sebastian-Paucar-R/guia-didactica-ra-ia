#!/bin/bash

echo "=== Creando estructura del Backend ==="

# Crear directorios
mkdir -p backend/app/api/v1/endpoints
mkdir -p backend/app/core
mkdir -p backend/app/services
mkdir -p backend/app/models
mkdir -p backend/app/utils
mkdir -p backend/knowledge_base
mkdir -p backend/tests

# Crear archivos vacíos
touch backend/app/__init__.py
touch backend/app/api/__init__.py
touch backend/app/api/v1/__init__.py
touch backend/app/api/v1/endpoints/__init__.py
touch backend/app/core/__init__.py
touch backend/app/services/__init__.py
touch backend/app/models/__init__.py
touch backend/app/utils/__init__.py

touch backend/.env
touch backend/README.md
touch backend/requirements.txt

echo "Estructura de carpetas creada correctamente."

# Crear el archivo principal main.py
cat > backend/app/main.py << 'EOF'
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.endpoints.chat import router as chat_router

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    debug=settings.DEBUG
)

# Middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # Cambiar en producción
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir rutas
app.include_router(chat_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "Backend del Tutor IA - Guía Didáctica RA funcionando correctamente"}
EOF

# Crear config.py
cat > backend/app/core/config.py << 'EOF'
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "Tutor IA - Guía Didáctica RA"
    VERSION: str = "0.1.0"
    DEBUG: bool = True

    class Config:
        env_file = ".env"

settings = Settings()
EOF

# Crear el endpoint del chat
cat > backend/app/api/v1/endpoints/chat.py << 'EOF'
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    user_id: str | None = None
    conversation_id: str | None = None

class ChatResponse(BaseModel):
    response: str
    status: str = "success"

@router.post("/chat", response_model=ChatResponse)
async def chat_with_tutor(request: ChatRequest):
    """Endpoint principal del Tutor IA"""
    user_message = request.message.strip()
    
    # Respuesta temporal (se mejorará con IA real)
    if any(word in user_message.lower() for word in ["hola", "saludo", "buenos"]):
        response_text = "¡Hola! Soy tu tutor IA especializado en normativas de Ingeniería de Software (ISO/IEC 25010 y otras). ¿En qué puedo ayudarte hoy?"
    else:
        response_text = f"Recibí tu mensaje: '{user_message}'. Por ahora estoy en fase de prueba. Pronto podré responderte con información precisa sobre normativas."
    
    return ChatResponse(response=response_text)
EOF

echo "Archivos principales creados."
echo "=== Estructura completa lista ==="
echo "Ahora ejecute: cd backend && python -m venv venv && source venv/bin/activate (o venv\Scripts\activate en Windows)"
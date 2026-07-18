import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic_settings import BaseSettings

# Configuración
class Settings(BaseSettings):
    APP_NAME: str = "Tutor IA - Guía Didáctica RA"
    VERSION: str = "0.1.0"
    DEBUG: bool = True

settings = Settings()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    debug=settings.DEBUG
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Importar el router del chat
from app.api.v1.endpoints.chat import router as chat_router
app.include_router(chat_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "✅ Backend del Tutor IA funcionando correctamente"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
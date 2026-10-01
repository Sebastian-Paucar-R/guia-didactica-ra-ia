"""GET /api/v1/salud: endpoint público para que la app sepa si el backend está disponible antes de dejar
escribir. No requiere autenticación ni toca el LLM de verdad (Ollama se simula con monkeypatch)."""
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.api.v1.endpoints.salud as salud_module
from app.services.rag_service import get_rag_service


def _cliente(rag) -> TestClient:
    app = FastAPI()
    app.include_router(salud_module.router, prefix="/api/v1")
    app.dependency_overrides[get_rag_service] = lambda: rag
    return TestClient(app)


def test_salud_no_requiere_autenticacion(rag, monkeypatch):
    monkeypatch.setattr(salud_module, "_ollama_responde", lambda: True)
    r = _cliente(rag).get("/api/v1/salud")
    assert r.status_code == 200


def test_salud_ok_cuando_ollama_responde(rag, monkeypatch):
    monkeypatch.setattr(salud_module, "_ollama_responde", lambda: True)
    datos = _cliente(rag).get("/api/v1/salud").json()
    assert datos["estado"] == "ok" and datos["ollama_disponible"] is True
    assert datos["modelo"] and datos["documentos_indexados"] == 0 and datos["chunks_indexados"] == 0


def test_salud_degradado_cuando_ollama_no_responde(rag, monkeypatch):
    monkeypatch.setattr(salud_module, "_ollama_responde", lambda: False)
    datos = _cliente(rag).get("/api/v1/salud").json()
    assert datos["estado"] == "degradado" and datos["ollama_disponible"] is False

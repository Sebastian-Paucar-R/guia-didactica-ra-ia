from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic_settings import BaseSettings
from app.api.v1.endpoints.chat import router as chat_router
from app.services.rag_service import RAGService
from fastapi.responses import FileResponse
from fastapi import HTTPException
import os

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/api/v1")

# Instancia del RAG para obtener información de documentos
rag_service = RAGService()

@app.get("/documentacion/{filename}")
async def get_document(filename: str):
    # Ruta relativa desde donde se ejecuta el servidor
    possible_paths = [
        os.path.join("documentacion", filename),
        os.path.join("backend", "documentacion", filename),
        os.path.join("..", "documentacion", filename),
        os.path.join(os.getcwd(), "documentacion", filename),
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return FileResponse(
                path,
                media_type="application/pdf",
                filename=filename
            )
    
    raise HTTPException(status_code=404, detail=f"Documento no encontrado: {filename}")

@app.get("/", response_class=HTMLResponse)
async def root():
    # Obtener lista de documentos
    docs_path = "documentacion"
    documentos = []
    if os.path.exists(docs_path):
        documentos = [f for f in os.listdir(docs_path) if f.lower().endswith(('.pdf', '.txt', '.md'))]

    docs_html = ""
    if documentos:
        for doc in documentos:
            docs_html += f'<li class="doc-item">📄 {doc}</li>'
    else:
        docs_html = '<li class="doc-item empty">No se encontraron documentos</li>'

    @app.get("/", response_class=HTMLResponse)
    async def root():
        docs_path = "documentacion"
    documentos = []
    if os.path.exists(docs_path):
        documentos = [f for f in os.listdir(docs_path) if f.lower().endswith(('.pdf', '.txt', '.md'))]

    docs_html = ""
    if documentos:
        for doc in documentos:
            docs_html += f'''
            <li class="doc-item">
                <span>📄 {doc}</span>
                <a href="/documentacion/{doc}" target="_blank" class="open-btn">Abrir</a>
            </li>'''
    else:
        docs_html = '<li class="doc-item empty">No se encontraron documentos</li>'

    html_content = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tutor IA - Guía Didáctica RA</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            color: #e2e8f0;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }}
        header {{
            background: rgba(15, 23, 42, 0.95);
            padding: 1rem 2rem;
            border-bottom: 1px solid #334155;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .logo {{ font-size: 1.35rem; font-weight: 700; color: #38bdf8; }}
        .status {{
            background: #065f46;
            color: #6ee7b7;
            padding: 0.35rem 1rem;
            border-radius: 9999px;
            font-size: 0.85rem;
            display: flex;
            align-items: center;
            gap: 0.4rem;
        }}
        .status::before {{
            content: '';
            width: 8px; height: 8px;
            background: #34d399;
            border-radius: 50%;
        }}
        .container {{
            display: grid;
            grid-template-columns: 300px 1fr 280px;
            gap: 1.2rem;
            padding: 1.2rem;
            flex: 1;
            max-width: 1600px;
            margin: 0 auto;
            width: 100%;
        }}
        .panel {{
            background: #1e293b;
            border-radius: 12px;
            border: 1px solid #334155;
            padding: 1.2rem;
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }}
        .panel h2 {{
            font-size: 0.95rem;
            margin-bottom: 1rem;
            color: #94a3b8;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }}
        .doc-list {{ list-style: none; overflow-y: auto; flex: 1; }}
        .doc-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.55rem 0.7rem;
            background: #0f172a;
            margin-bottom: 0.45rem;
            border-radius: 8px;
            font-size: 0.85rem;
            border-left: 3px solid #38bdf8;
            gap: 0.5rem;
        }}
        .doc-item span {{ overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
        .open-btn {{
            background: #0369a1;
            color: white;
            padding: 0.25rem 0.6rem;
            border-radius: 6px;
            text-decoration: none;
            font-size: 0.75rem;
            white-space: nowrap;
        }}
        .open-btn:hover {{ background: #0284c7; }}
        .chat-container {{ display: flex; flex-direction: column; height: calc(100vh - 120px); }}
        .messages {{
            flex: 1;
            overflow-y: auto;
            padding: 1rem;
            display: flex;
            flex-direction: column;
            gap: 0.9rem;
        }}
        .message {{
            max-width: 85%;
            padding: 0.85rem 1.1rem;
            border-radius: 12px;
            line-height: 1.45;
            white-space: pre-wrap;
            font-size: 0.95rem;
        }}
        .user {{ background: #0369a1; align-self: flex-end; border-bottom-right-radius: 4px; }}
        .assistant {{ background: #334155; align-self: flex-start; border-bottom-left-radius: 4px; }}
        .input-area {{
            padding: 1rem;
            border-top: 1px solid #334155;
            display: flex;
            gap: 0.7rem;
        }}
        #user-input {{
            flex: 1;
            background: #0f172a;
            border: 1px solid #475569;
            color: #e2e8f0;
            padding: 0.75rem 1rem;
            border-radius: 8px;
            font-size: 0.95rem;
            outline: none;
        }}
        #user-input:focus {{ border-color: #38bdf8; }}
        button {{
            background: #0284c7;
            color: white;
            border: none;
            padding: 0.75rem 1.3rem;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
        }}
        button:hover {{ background: #0369a1; }}
        button:disabled {{ background: #475569; cursor: not-allowed; }}
        .history-list {{
            list-style: none;
            overflow-y: auto;
            flex: 1;
            font-size: 0.85rem;
        }}
        .history-item {{
            padding: 0.5rem 0.7rem;
            background: #0f172a;
            margin-bottom: 0.4rem;
            border-radius: 6px;
            cursor: pointer;
            border-left: 3px solid #64748b;
        }}
        .history-item:hover {{ border-left-color: #38bdf8; }}
        .clear-btn {{
            background: #7f1d1d;
            font-size: 0.8rem;
            padding: 0.4rem 0.8rem;
            margin-top: 0.8rem;
        }}
    </style>
</head>
<body>
    <header>
        <div class="logo">Tutor IA · Guía Didáctica RA</div>
        <div class="status">Sistema operativo</div>
    </header>

    <div class="container">
        <!-- Documentos -->
        <aside class="panel">
            <h2>Documentos cargados</h2>
            <ul class="doc-list">{docs_html}</ul>
            <p style="margin-top: 1rem; font-size: 0.8rem; color: #94a3b8;">
                Fragmentos procesados: <strong>126</strong>
            </p>
        </aside>

        <!-- Chat -->
        <main class="panel chat-container">
            <h2>Chat de prueba con el Tutor IA</h2>
            <div class="messages" id="messages"></div>
            <div class="input-area">
                <input type="text" id="user-input" placeholder="Escribe tu pregunta sobre normativas..." 
                       onkeypress="if(event.key==='Enter') sendMessage()">
                <button onclick="sendMessage()" id="send-btn">Enviar</button>
            </div>
        </main>

        <!-- Historial -->
        <aside class="panel">
            <h2>Historial del chat</h2>
            <ul class="history-list" id="history-list"></ul>
            <button class="clear-btn" onclick="clearHistory()">Limpiar historial</button>
        </aside>
    </div>

    <script>
        const messagesDiv = document.getElementById('messages');
        const historyList = document.getElementById('history-list');
        const input = document.getElementById('user-input');
        const sendBtn = document.getElementById('send-btn');

        function loadHistory() {{
            const history = JSON.parse(localStorage.getItem('tutor_history') || '[]');
            messagesDiv.innerHTML = '';
            historyList.innerHTML = '';
            
            history.forEach((msg, index) => {{
                addMessage(msg.role, msg.content, false);
                if (msg.role === 'user') {{
                    const li = document.createElement('li');
                    li.className = 'history-item';
                    li.textContent = msg.content.substring(0, 45) + (msg.content.length > 45 ? '...' : '');
                    li.onclick = () => {{
                        input.value = msg.content;
                        input.focus();
                    }};
                    historyList.appendChild(li);
                }}
            }});
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }}

        function saveMessage(role, content) {{
            const history = JSON.parse(localStorage.getItem('tutor_history') || '[]');
            history.push({{ role, content, timestamp: new Date().toISOString() }});
            localStorage.setItem('tutor_history', JSON.stringify(history));
        }}

        function addMessage(role, content, save = true) {{
            const div = document.createElement('div');
            div.className = `message ${{role === 'user' ? 'user' : 'assistant'}}`;
            div.textContent = content;
            messagesDiv.appendChild(div);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
            if (save) saveMessage(role, content);
        }}

        async function sendMessage() {{
            const text = input.value.trim();
            if (!text) return;

            addMessage('user', text);
            input.value = '';
            sendBtn.disabled = true;
            sendBtn.textContent = 'Pensando...';

            // Actualizar historial lateral
            const li = document.createElement('li');
            li.className = 'history-item';
            li.textContent = text.substring(0, 45) + (text.length > 45 ? '...' : '');
            historyList.prepend(li);

            try {{
                const res = await fetch('/api/v1/chat', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ message: text }})
                }});
                const data = await res.json();
                addMessage('assistant', data.response || 'Sin respuesta');
            }} catch (err) {{
                addMessage('assistant', 'Error de conexión con el servidor.');
            }} finally {{
                sendBtn.disabled = false;
                sendBtn.textContent = 'Enviar';
            }}
        }}

        function clearHistory() {{
            if (confirm('¿Desea borrar todo el historial de chat?')) {{
                localStorage.removeItem('tutor_history');
                messagesDiv.innerHTML = '';
                historyList.innerHTML = '';
            }}
        }}

        loadHistory();
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)
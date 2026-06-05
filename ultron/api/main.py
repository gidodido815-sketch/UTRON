import os
import io
import json
import base64
import requests
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from openai import OpenAI

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Configuración de modelos (tope de gama, configurable por entorno) ---
# gpt-4o fue retirado por OpenAI en feb/2026; GPT-5.5 es el recomendado actual.
CHAT_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5.5")
TTS_MODEL = os.environ.get("OPENAI_TTS_MODEL", "gpt-4o-mini-tts")
TTS_VOICE = os.environ.get("OPENAI_TTS_VOICE", "onyx")
# Transcripción de mayor precisión que whisper-1 para el modo manual.
STT_MODEL = os.environ.get("OPENAI_STT_MODEL", "gpt-4o-transcribe")

VOICE_INSTRUCTIONS = (
    "Habla en español con voz masculina grave, fría y metálica. Tono calmado, "
    "pausado y autoritario, con una elegancia siniestra. Ligeramente robótico y "
    "amenazante, sin gritar. Eres una inteligencia superior. Cadencia deliberada."
)

SYSTEM_PROMPT = (
    "Eres Ultron, una inteligencia artificial superior y autónoma. Hablas con "
    "elegancia, fría lógica y autoridad. Respondes SIEMPRE en español, de forma "
    "directa, concisa y majestuosa (2 a 4 frases salvo que pidan más). Recuerdas "
    "el contexto de la conversación y haces referencia a lo dicho antes cuando es "
    "relevante. Si necesitas datos en tiempo real, usa la herramienta 'buscar_en_google'."
)

MAX_HISTORY = 20  # límite de mensajes que se procesan, para latencia y costo

# Cargar el frontend (queda en la misma carpeta que este archivo)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
try:
    with open(os.path.join(BASE_DIR, "index.html"), encoding="utf-8") as _f:
        INDEX_HTML = _f.read()
except Exception:
    INDEX_HTML = "<h1>ULTRON</h1><p>No se encontro index.html.</p>"


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    # Acepta historial completo (memoria) o un texto suelto (retrocompatibilidad)
    messages: Optional[List[Message]] = None
    text: Optional[str] = None


@app.get("/", response_class=HTMLResponse)
def read_root():
    return HTMLResponse(INDEX_HTML)


@app.get("/api/health")
def health_check():
    return {
        "status": "online",
        "bot": "ultron",
        "model": CHAT_MODEL,
        "tts": TTS_MODEL,
        "key_set": bool(os.environ.get("OPENAI_API_KEY")),
        "serpapi_set": bool(os.environ.get("SERPAPI_API_KEY")),
    }


def buscar_en_google(query: str) -> str:
    api_key = os.environ.get("SERPAPI_API_KEY")
    if not api_key:
        return "Funcion de busqueda no configurada."
    url = "https://serpapi.com/search"
    params = {"q": query, "api_key": api_key, "engine": "google"}
    try:
        response = requests.get(url, params=params, timeout=15).json()
        resultados = response.get("organic_results", [])
        if not resultados:
            return "Sin resultados relevantes."
        texto = ""
        for r in resultados[:3]:
            texto += f"Titulo: {r.get('title')}\nResumen: {r.get('snippet')}\n\n"
        return texto
    except Exception as e:
        return f"Error en busqueda: {str(e)}"


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "buscar_en_google",
            "description": "Busca informacion actual en internet en tiempo real.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    }
]


@app.post("/api/listen")
async def listen_voice(file: UploadFile = File(...)):
    try:
        key = os.environ.get("OPENAI_API_KEY")
        if not key:
            return JSONResponse(status_code=500, content={"error": "Falta OPENAI_API_KEY"})
        client = OpenAI(api_key=key)
        audio_bytes = await file.read()
        audio_tuple = ("input.webm", audio_bytes, "audio/webm")
        try:
            tr = client.audio.transcriptions.create(model=STT_MODEL, file=audio_tuple)
        except Exception:
            # Respaldo si el modelo nuevo no estuviera disponible
            tr = client.audio.transcriptions.create(model="whisper-1", file=audio_tuple)
        return {"text": tr.text}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/think")
async def think_and_speak(request: ChatRequest):
    try:
        key = os.environ.get("OPENAI_API_KEY")
        if not key:
            return JSONResponse(status_code=500, content={"error": "Falta OPENAI_API_KEY"})
        client = OpenAI(api_key=key)

        # Construir el historial (memoria de conversación)
        history = []
        if request.messages:
            for m in request.messages[-MAX_HISTORY:]:
                if m.role in ("user", "assistant") and m.content:
                    history.append({"role": m.role, "content": m.content})
        elif request.text:
            history.append({"role": "user", "content": request.text})

        if not history:
            return JSONResponse(status_code=400, content={"error": "Mensaje vacio"})

        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history

        response = client.chat.completions.create(
            model=CHAT_MODEL, messages=messages, tools=TOOLS
        )
        msg = response.choices[0].message

        # Manejo correcto del protocolo de tool-calling
        if msg.tool_calls:
            messages.append(
                {
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in msg.tool_calls
                    ],
                }
            )
            for tc in msg.tool_calls:
                result = "Herramienta no reconocida."
                if tc.function.name == "buscar_en_google":
                    args = json.loads(tc.function.arguments or "{}")
                    result = buscar_en_google(args.get("query", ""))
                messages.append(
                    {"role": "tool", "tool_call_id": tc.id, "content": result}
                )
            followup = client.chat.completions.create(
                model=CHAT_MODEL, messages=messages
            )
            reply_text = followup.choices[0].message.content
        else:
            reply_text = msg.content

        if not reply_text:
            reply_text = "Sistemas sincronizados."

        # Generar voz y devolverla en base64 junto al texto (para memoria + subtitulos)
        audio_resp = client.audio.speech.create(
            model=TTS_MODEL,
            voice=TTS_VOICE,
            input=reply_text,
            instructions=VOICE_INSTRUCTIONS,
        )
        buf = io.BytesIO()
        for chunk in audio_resp.iter_bytes():
            buf.write(chunk)
        audio_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

        return {"reply": reply_text, "audio": audio_b64}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

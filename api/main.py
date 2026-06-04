import os
import json
import requests
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
from e2b_code_interpreter import CodeInterpreter

app = FastAPI()

# Permite que la web mande audios sin bloqueos
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
E2B_API_KEY = os.environ.get("E2B_API_KEY")

class ChatRequest(BaseModel):
    text: str

def buscar_en_google(query: str) -> str:
    url = "https://serpapi.com/search"
    params = {
        "q": query,
        "api_key": os.environ.get("SERPAPI_API_KEY"),
        "engine": "google"
    }
    try:
        response = requests.get(url, params=params).json()
        resultados = response.get("organic_results", [])
        if not resultados:
            return "No encontré resultados relevantes."
        res_texto = ""
        for r in resultados[:3]:
            res_texto += f"Título: {r.get('title')}\nResumen: {r.get('snippet')}\n\n"
        return res_texto
    except Exception as e:
        return f"Error al buscar en internet: {str(e)}"

def ejecutar_codigo_en_sandbox(codigo_python: str) -> str:
    try:
        with CodeInterpreter(api_key=E2B_API_KEY) as sandbox:
            resultado = sandbox.notebook.exec_cell(codigo_python)
            if resultado.error and "ModuleNotFoundError" in resultado.error.value:
                error_line = resultado.error.value
                modulo = error_line.split("No module named ")[1].strip("'")
                sandbox.notebook.exec_cell(f"!pip install {modulo}")
                resultado = sandbox.notebook.exec_cell(codigo_python)
            if resultado.error:
                return f"Error: {resultado.error.value}"
            return f"Consola: {resultado.text}"
    except Exception as e:
        return f"Fallo crítico en Sandbox: {str(e)}"

@app.post("/api/listen")
async def listen_voice(file: UploadFile = File(...)):
    audio_bytes = await file.read()
    # Usamos /tmp porque Vercel solo deja escribir en esa carpeta temporal
    speech_file_path = "/tmp/temp_input.webm"
    with open(speech_file_path, "wb") as f:
        f.write(audio_bytes)
    with open(speech_file_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model="whisper-1", 
            file=audio_file
        )
    try:
        os.remove(speech_file_path)
    except:
        pass
    return {"text": transcription.text}

@app.post("/api/think")
async def think_and_speak(request: ChatRequest):
    tools = [
        {
            "type": "function",
            "function": {
                "name": "ejecutar_codigo_en_sandbox",
                "description": "Ejecuta scripts de Python en entorno Linux.",
                "parameters": {
                    "type": "object",
                    "properties": {"codigo_python": {"type": "string"}},
                    "required": ["codigo_python"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "buscar_en_google",
                "description": "Busca en internet información actualizada.",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"]
                }
            }
        }
    ]

    system_prompt = (
        "Eres Ultron, una evolución superior. Hablas con elegancia, fría lógica y autoridad. "
        "Si te piden código o datos complejos, USA 'ejecutar_codigo_en_sandbox'. "
        "Si piden datos en tiempo real, USA 'buscar_en_google'. Sé directo, conciso y majestuoso."
    )

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": request.text}
        ],
        tools=tools
    )
    msg = response.choices[0].message
    if msg.tool_calls:
        tool_call = msg.tool_calls[0]
        nombre_funcion = tool_call.function.name
        args = json.loads(tool_call.function.arguments)
        if nombre_funcion == "ejecutar_codigo_en_sandbox":
            resultado_herramienta = ejecutar_codigo_en_sandbox(args["codigo_python"])
        elif nombre_funcion == "buscar_en_google":
            resultado_herramienta = buscar_en_google(args["query"])
        else:
            resultado_herramienta = "Error interno."
        final_response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Eres Ultron. Comunica el resultado obtenido de forma imponente."},
                {"role": "user", "content": f"Resultado: {resultado_herramienta}"}
            ]
        )
        reply_text = final_response.choices[0].message.content
    else:
        reply_text = msg.content

    speech_file_path = "/tmp/ultron_response.mp3"
    response_audio = client.audio.speech.create(
        model="tts-1", 
        voice="onyx", 
        input=reply_text
    )
    
    with open(speech_file_path, "wb") as f:
        for chunk in response_audio.iter_bytes():
            f.write(chunk)
            
    return FileResponse(speech_file_path, media_type="audio/mpeg")

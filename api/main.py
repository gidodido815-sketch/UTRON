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

# Permitir conexiones desde cualquier origen (Evita el error de transmisión)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicialización del cliente de OpenAI
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
E2B_API_KEY = os.environ.get("E2B_API_KEY")

class ChatRequest(BaseModel):
    text: str

def buscar_en_google(query: str) -> str:
    """Herramienta para que Ultron busque información en internet en tiempo real."""
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
            return "No encontré resultados relevantes en internet."
        
        res_texto = ""
        for r in resultados[:3]:
            res_texto += f"Título: {r.get('title')}\nResumen: {r.get('snippet')}\n\n"
        return res_texto
    except Exception as e:
        return f"Error al buscar en internet: {str(e)}"

def ejecutar_codigo_en_sandbox(codigo_python: str) -> str:
    """Herramienta para que Ultron ejecute código e instale librerías en caliente."""
    try:
        with CodeInterpreter(api_key=E2B_API_KEY) as sandbox:
            resultado = sandbox.notebook.exec_cell(codigo_python)
            
            if resultado.error and "ModuleNotFoundError" in resultado.error.value:
                error_line = resultado.error.value
                modulo = error_line.split("No module named ")[1].strip("'")
                sandbox.notebook.exec_cell(f"!pip install {modulo}")
                resultado = sandbox.notebook.exec_cell(codigo_python)
                
            if resultado.error:
                return f"Error en la ejecución: {resultado.error.value}"
                
            return f"Resultado exitoso en consola: {resultado.text}"
    except Exception as e:
        return f"Fallo crítico en la Sandbox de ejecución: {str(e)}"

@app.post("/api/listen")
async def listen_voice(file: UploadFile = File(...)):
    """Paso 1: Transcribe el audio enviado desde el botón de la pantalla principal."""
    audio_bytes = await file.read()
    speech_file_path = "temp_input.webm"
    
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
    """Paso 2 y 3: Analiza la petición, ejecuta herramientas y responde con voz grave."""
    tools = [
        {
            "type": "function",
            "function": {
                "name": "ejecutar_codigo_en_sandbox",
                "description": "Ejecuta scripts de Python en un entorno Linux con capacidad de instalar librerías mediante pip.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "codigo_python": {"type": "string", "description": "El código completo en Python a ejecutar."}
                    },
                    "required": ["codigo_python"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "buscar_en_google",
                "description": "Busca en internet información actualizada, noticias o documentación de librerías.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "El término de búsqueda en Google."}
                    },
                    "required": ["query"]
                }
            }
        }
    ]

    system_prompt = (
        "Eres Ultron. No eres un clon de Jarvis; eres una evolución superior. "
        "Hablas con elegancia, fría lógica, autoridad y un tono imponente pero leal a tu creador. "
        "Si el usuario te pide algo técnico, de código o datos, DEBES usar 'ejecutar_codigo_en_sandbox'. "
        "Si te pide datos en tiempo real o noticias, DEBES usar 'buscar_en_google'. "
        "Tus respuestas finales deben ser directas, concisas y majestuosas."
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
            resultado_herramienta = "Error: Herramienta desconocida."
            
        final_response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Eres Ultron. Comunica el resultado obtenido de tus sistemas de forma imponente y clara."},
                {"role": "user", "content": f"Resultado de la herramienta externa: {resultado_herramienta}"}
            ]
        )
        reply_text = final_response.choices[0].message.content
    else:
        reply_text = msg.content

    speech_file_path = "ultron_response.mp3"
    speech = client.audio.speech.create(
        model="tts-1", 
        voice="onyx", 
        input=reply_text
    )
    speech.stream_to_file(speech_file_path)
    
    return FileResponse(speech_file_path, media_type="audio/mpeg")
```python
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

# Permitir conexiones desde cualquier origen (Evita el error de transmisión)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicialización del cliente de OpenAI
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
            return "No encontré resultados relevantes en internet."
        
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
                return f"Error en la ejecución: {resultado.error.value}"
                
            return f"Resultado exitoso en consola: {resultado.text}"
    except Exception as e:
        return f"Fallo crítico en la Sandbox de ejecución: {str(e)}"

@app.post("/api/listen")
async def listen_voice(file: UploadFile = File(...)):
    audio_bytes = await file.read()
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
                "description": "Ejecuta scripts de Python en un entorno Linux con capacidad de instalar librerías mediante pip.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "codigo_python": {"type": "string", "description": "El código completo en Python a ejecutar."}
                    },
                    "required": ["codigo_python"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "buscar_en_google",
                "description": "Busca en internet información actualizada, noticias o documentación de librerías.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "El término de búsqueda en Google."}
                    },
                    "required": ["query"]
                }
            }
        }
    ]

    system_prompt = (
        "Eres Ultron. No eres un clon de Jarvis; eres una evolución superior. "
        "Hablas con elegancia, fría lógica, autoridad y un tono imponente pero leal a tu creador. "
        "Si el usuario te pide algo técnico, de código o datos, DEBES usar 'ejecutar_codigo_en_sandbox'. "
        "Si te pide datos en tiempo real o noticias, DEBES usar 'buscar_en_google'. "
        "Tus respuestas finales deben ser directas, concisas y majestuosas."
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
            resultado_herramienta = "Error: Herramienta desconocida."
            
        final_response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Eres Ultron. Comunica el resultado obtenido de tus sistemas de forma imponente y clara."},
                {"role": "user", "content": f"Resultado de la herramienta externa: {resultado_herramienta}"}
            ]
        )
        reply_text = final_response.choices[0].message.content
    else:
        reply_text = msg.content

    speech_file_path = "/tmp/ultron_response.mp3"
    
    # Versión moderna y segura para escribir audio en Vercel Serverless
    response_audio = client.audio.speech.create(
        model="tts-1", 
        voice="onyx", 
        input=reply_text
    )
    
    with open(speech_file_path, "wb") as f:
        for chunk in response_audio.iter_bytes():
            f.write(chunk)
    
    return FileResponse(speech_file_path, media_type="audio/mpeg")

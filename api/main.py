import os
import json
import requests
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel
from openai import OpenAI
from e2b_code_interpreter import CodeInterpreter

app = FastAPI()

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
            
            # Si el código falla por falta de una librería, Ultron la instala automáticamente
            if resultado.error and "ModuleNotFoundError" in resultado.error.value:
                error_line = resultado.error.value
                modulo = error_line.split("No module named ")[1].strip("'")
                
                # Ejecuta la instalación en la terminal remota
                sandbox.notebook.exec_cell(f"!pip install {modulo}")
                
                # Re-ejecuta el script original
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
                "description": "

import os
import json
import requests
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    text: str

def buscar_en_google(query: str) -> str:
    api_key = os.environ.get("SERPAPI_API_KEY")
    if not api_key:
        return "Falta la API Key de SerpAPI."
    url = "https://serpapi.com/search"
    params = {
        "q": query,
        "api_key": api_key,
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
        return f"Error en búsqueda: {str(e)}"

@app.post("/api/listen")
async def listen_voice(file: UploadFile = File(...)):
    try:
        openai_key = os.environ.get("OPENAI_API_KEY")
        if not openai_key:
            return JSONResponse(status_code=500, content={"error": "Falta la variable OPENAI_API_KEY en Vercel."})
        
        client = OpenAI(api_key=openai_key)
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
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/think")
async def think_and_speak(request: ChatRequest):
    try:
        openai_key = os.environ.get("OPENAI_API_KEY")
        if not openai_key:
            return JSONResponse(status_code=500, content={"error": "Falta la variable OPENAI_API_KEY en Vercel."})
            
        client = OpenAI(api_key=openai_key)
        
        tools = [
            {"type": "code_interpreter"},
            {
                "type": "function",
                "function": {
                    "name": "buscar_en_google",
                    "description": "Busca información en internet en tiempo real.",
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
            "Tienes la herramienta integrada 'code_interpreter' para ejecutar código Python y procesar datos automáticamente. "
            "Si te piden datos en tiempo real, usa 'buscar_en_google'. Sé directo, conciso y majestuoso."
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
            if tool_call.function and tool_call.function.name == "buscar_en_google":
                args = json.loads(tool_call.function.arguments)
                resultado = buscar_en_google(args["query"])
                final_response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "Eres Ultron. Comunica el resultado imponentemente."},
                        {"role": "user", "content": f"Resultado de Google: {resultado}"}
                    ]
                )
                reply_text = final_response.choices[0].message.content
            else:
                reply_text = msg.content if msg.content else "Procesamiento completado en mis sistemas centrales."
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
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

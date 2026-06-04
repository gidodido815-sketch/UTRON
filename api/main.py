import os
import io
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

@app.get("/")
def read_root():
    return {"status": "ready", "bot": "ultron"}

@app.post("/api/listen")
async def listen_voice(file: UploadFile = File(...)):
    try:
        openai_key = os.environ.get("OPENAI_API_KEY")
        if not openai_key:
            return JSONResponse(status_code=500, content={"error": "Falta la variable OPENAI_API_KEY"})
        
        client = OpenAI(api_key=openai_key)
        audio_bytes = await file.read()
        
        # Procesamiento directo en memoria RAM (Evita errores de escritura en Vercel)
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "input.webm"
        
        transcription = client.audio.transcriptions.create(
            model="whisper-1", 
            file=audio_file
        )
        
        return {"text": transcription.text}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/think")
async def think_and_speak(request: ChatRequest):
    try:
        openai_key = os.environ.get("OPENAI_API_KEY")
        if not openai_key:
            return JSONResponse(status_code=500, content={"error": "Falta la variable OPENAI_API_KEY"})
            
        client = OpenAI(api_key=openai_key)
        
        system_prompt = (
            "Eres Ultron, una evolución superior. Hablas con elegancia, fría lógica y autoridad. "
            "Sé directo, conciso y majestuoso."
        )

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": request.text}
            ]
        )
        reply_text = response.choices[0].message.content

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

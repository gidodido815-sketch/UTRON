@app.post("/api/listen")
async def listen_voice(file: UploadFile = File(...)):
    try:
        openai_key = os.environ.get("OPENAI_API_KEY")
        if not openai_key:
            return JSONResponse(status_code=500, content={"error": "Falta la variable OPENAI_API_KEY"})
        
        client = OpenAI(api_key=openai_key)
        audio_bytes = await file.read()
        
        # Estructura de tupla explícita requerida por las últimas versiones del SDK de OpenAI
        audio_tuple = ("input.webm", audio_bytes, "audio/webm")
        
        transcription = client.audio.transcriptions.create(
            model="whisper-1", 
            file=audio_tuple
        )
        
        return {"text": transcription.text}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

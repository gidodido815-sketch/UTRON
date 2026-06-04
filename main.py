from fastapi import FastAPI
from pydantic import BaseModel
import os

app = FastAPI()

class Query(BaseModel):
    prompt: str

@app.post("/api/ultron")
async def chat_ultron(query: Query):
    # Aquí irá la lógica del LLM y la conexión a la sandbox
    return {"response": f"Ultron procesando: {query.prompt}"}
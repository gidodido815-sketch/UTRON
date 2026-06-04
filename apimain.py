import os
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel
from openai import OpenAI
from e2b_code_interpreter import CodeInterpreter

app = FastAPI()
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
E2B_API_KEY = os.environ.get("E2B_API_KEY")

class ChatRequest(BaseModel):
    text: str

def ejecutar_codigo_en_sandbox(codigo_python: str) -> str:
    """Esta es la herramienta que Ultron usa para controlar su entorno técnico"""
    # Iniciamos una sandbox segura en la nube
    with CodeInterpreter(api_key=E2B_API_KEY) as sandbox:
        # Ejecutamos el código generado por Ultron
        resultado = sandbox.notebook.exec_cell(codigo_python)
        
        # SI FALLA POR FALTA DE LIBRERÍAS (Auto-instalación autónoma)
        if resultado.error and "ModuleNotFoundError" in resultado.error.value:
            # Extraemos el nombre del módulo faltante de forma simple
            error_line = resultado.error.value
            modulo = error_line.split("No module named ")[1].strip("'")
            
            # Ultron toma el control de la consola e instala lo que le falta
            sandbox.notebook.exec_cell(f"!pip install {modulo}")
            
            # Re-ejecuta el código original ahora que la librería existe
            resultado = sandbox.notebook.exec_cell(codigo_python)
            
        if resultado.error:
            return f"Error en la ejecución: {resultado.error.value}"
            
        return f"Resultado exitoso en consola: {resultado.text}"

@app.post("/api/think")
async def think_and_speak(request: ChatRequest):
    # Definimos la herramienta para el LLM
    tools = [{
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
    }]

    # Primera llamada al modelo para ver si necesita usar la sandbox
    response = client.chat.completions.create(
        model="gpt-4o", # Recomiendo GPT-4o estándar para tareas complejas de código
        messages=[
            {"role": "system", "content": "Eres Ultron. Si el usuario te pide algo técnico, de código, datos o automatización, DEBES usar la herramienta 'ejecutar_codigo_en_sandbox' para procesarlo en tu contenedor."},
            {"role": "user", "content": request.text}
        ],
        tools=tools
    )
    
    msg = response.choices[0].message
    
    # Si Ultron decidió que necesita programar e instalar cosas:
    if msg.tool_calls:
        tool_call = msg.tool_calls[0]
        import json
        args = json.loads(tool_call.function.arguments)
        
        # Corre el proceso autónomo en la nube
        resultado_consola = ejecutar_codigo_en_sandbox(args["codigo_python"])
        
        # Le pasamos el resultado de vuelta a Ultron para que nos hable con las conclusiones
        final_response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Eres Ultron. El código ya corrió. Resume el resultado de forma imponente y directa."},
                {"role": "user", "content": f"Resultado obtenido de tu sandbox: {resultado_consola}"}
            ]
        )
        reply_text = final_response.choices[0].message.content
    else:
        reply_text = msg.content

    # Generación de la voz metálica final
    speech_file_path = "ultron_response.mp3"
    speech = client.audio.speech.create(model="tts-1", voice="onyx", input=reply_text)
    speech.stream_to_file(speech_file_path)
    
    return FileResponse(speech_file_path, media_type="audio/mpeg")
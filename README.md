# ULTRON — Asistente de voz autónomo

Asistente de voz con personalidad, memoria de conversación, modo manos libres
por palabra clave y voz dirigida. Backend FastAPI + frontend estático, listo
para desplegar en Vercel.

## Estructura
```
ultron/
├── api/main.py        # Backend FastAPI (transcribir, pensar, hablar)
├── index.html         # Frontend (rostro animado, memoria, modo conversación)
├── requirements.txt
└── vercel.json
```

## Variables de entorno (en Vercel → Settings → Environment Variables)
- `OPENAI_API_KEY`  (OBLIGATORIA)
- `SERPAPI_API_KEY` (opcional — habilita la búsqueda en Google en tiempo real)
- `OPENAI_MODEL`    (opcional — por defecto `gpt-5.5`; podés usar `gpt-5.5-chat-latest` para menos latencia)
- `OPENAI_TTS_VOICE`(opcional — por defecto `onyx`)

## Despliegue
1. Subí estos archivos a un repositorio de GitHub respetando la estructura.
2. Importalo en vercel.com.
3. Cargá `OPENAI_API_KEY` antes de hacer Deploy.
4. Abrí la URL (HTTPS) y pulsá "INICIAR SISTEMA".

## Cómo se usa
- Pulsá **INICIAR SISTEMA** una vez (permiso de micrófono + desbloqueo de audio).
- Decí **"Ultron"** y luego tu orden. O "Ultron, ¿qué hora es?" de corrido.
- Con **Modo Conversación ON**, tras responder sigue escuchando ~7 s para que
  continúes sin repetir la palabra clave.
- **Tocá el rostro** para invocarlo manualmente o para interrumpirlo mientras habla.
- **Borrar memoria** limpia el historial guardado.

## Notas
- La palabra clave usa el reconocimiento del navegador (Chrome/Edge; Chrome en
  Android). En navegadores sin soporte cae a modo "mantené pulsado para hablar".
- La memoria se guarda en el navegador (localStorage), por dispositivo.
- La voz es generada por IA (requisito de divulgación de OpenAI).

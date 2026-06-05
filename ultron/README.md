# ULTRON — Asistente de voz autónomo

Asistente de voz con personalidad, memoria de conversación, modo manos libres
por palabra clave y voz dirigida. UNA sola función de Python (FastAPI) sirve
tanto la página como la API, listo para Vercel.

## Estructura (IMPORTANTE: respetar esto)
```
ultron/
├── api/
│   ├── main.py        # Backend: sirve la web + /api/listen + /api/think
│   └── index.html     # Frontend (lo sirve main.py)
├── requirements.txt
└── vercel.json        # Manda TODO el tráfico a la función
```

## Variables de entorno (Vercel → Settings → Environment Variables)
- `OPENAI_API_KEY`  (OBLIGATORIA)
- `SERPAPI_API_KEY` (opcional — búsqueda en Google en tiempo real)
- `OPENAI_MODEL`    (opcional — por defecto `gpt-5.5`)
- `OPENAI_TTS_VOICE`(opcional — por defecto `onyx`)

## Redespliegue (si ya tenías una versión rota)
1. En Vercel, borrá los archivos viejos del proyecto (sobre todo el index.html
   que estaba en la raíz y el vercel.json viejo).
2. Subí esta carpeta COMPLETA respetando la estructura de arriba.
3. Verificá que `OPENAI_API_KEY` esté cargada.
4. Deploy. Probá entrando a `/api/health`: debe responder un JSON con el estado.

## Uso
- Pulsá INICIAR SISTEMA una vez (permiso de micrófono + audio).
- Decí "Ultron" y tu orden, o "Ultron, ¿qué hora es?" de corrido.
- Modo Conversación ON: tras responder sigue escuchando ~7 s.
- Tocá el rostro para invocarlo manualmente o interrumpirlo.
- Borrar memoria limpia el historial guardado en el navegador.

## Diagnóstico rápido
- `tudominio.vercel.app/api/health` → si responde JSON, el backend está vivo.
- Si "Invocaciones de funciones" sigue en 0 en Vercel, la estructura de carpetas
  no se subió bien (el `main.py` debe estar dentro de `api/`).

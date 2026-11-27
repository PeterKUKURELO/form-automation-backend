from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import shutil
import asyncio
import json
import os
from pathlib import Path
from uuid import uuid4

from config import EXCEL_DIR
from selenium_worker import procesar_excel_streaming

app = FastAPI(
    title="Form Automation Backend",
    version="1.0.0",
)

# ─────────────────────────────────────────────
# CORS
# ─────────────────────────────────────────────

cors_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "*").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=cors_origins != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────
# GLOBAL LOCK (CLAVE DEL FIX)
# ─────────────────────────────────────────────

PROCESSING = False
STOP_REQUESTED = False


# ─────────────────────────────────────────────
# Health endpoint
# ─────────────────────────────────────────────

@app.get("/health", tags=["system"])
async def health():
    return {
        "status": "ok",
        "processing": PROCESSING,
        "stopping": STOP_REQUESTED,
    }


@app.post("/stop", tags=["automation"])
async def stop_processing():
    global STOP_REQUESTED

    if not PROCESSING:
        return {
            "status": "idle",
            "message": "No hay un proceso en ejecución",
        }

    STOP_REQUESTED = True
    return {
        "status": "stopping",
        "message": "El proceso se detendrá al terminar el registro actual",
    }


# ─────────────────────────────────────────────
# Upload endpoint
# ─────────────────────────────────────────────

@app.post("/upload/", tags=["automation"])
async def upload_excel(
    file: UploadFile = File(...),
    headless: bool = Form(True),
):
    global PROCESSING, STOP_REQUESTED

    if PROCESSING:
        raise HTTPException(
            status_code=409,
            detail="Ya hay un proceso en ejecución"
        )

    PROCESSING = True
    STOP_REQUESTED = False
    print("🔥 /upload llamado")

    # Guardar con un nombre interno único para impedir colisiones y evitar que
    # el nombre enviado por el cliente pueda escapar del directorio temporal.
    upload_dir = Path(EXCEL_DIR)
    extension = Path(file.filename or "upload.xlsx").suffix
    file_location = upload_dir / f"{uuid4().hex}{extension}"

    try:
        upload_dir.mkdir(parents=True, exist_ok=True)
        with open(file_location, "wb") as f:
            shutil.copyfileobj(file.file, f)
    except Exception as exc:
        PROCESSING = False
        raise HTTPException(
            status_code=500,
            detail="No se pudo guardar temporalmente el archivo",
        ) from exc
    finally:
        await file.close()

    async def event_generator():
        global PROCESSING, STOP_REQUESTED
        worker = procesar_excel_streaming(str(file_location), headless)
        stop_announced = False
        try:
            async for resultado in worker:
                try:
                    event_name = json.loads(resultado).get("evento")
                except (json.JSONDecodeError, AttributeError):
                    event_name = None

                if STOP_REQUESTED and not stop_announced and event_name != "fin":
                    stop_announced = True
                    yield "data: " + json.dumps({
                        "evento": "deteniendo",
                        "mensaje": "Terminando el registro actual...",
                    }, ensure_ascii=False) + "\n\n"

                yield f"data: {resultado}\n\n"

                safe_stop_events = {
                    "inicio",
                    "batch_inicio",
                    "procesando",
                    "registro_preparado",
                    "resultado",
                    "batch_pausa",
                    "error",
                    "error_batch",
                }
                if STOP_REQUESTED and event_name in safe_stop_events:
                    yield "data: " + json.dumps({
                        "evento": "detenido",
                        "mensaje": "Proceso detenido por el usuario",
                    }, ensure_ascii=False) + "\n\n"
                    break

                await asyncio.sleep(0.01)
        finally:
            try:
                await worker.aclose()
            except Exception:
                pass
            # 🔓 LIBERAR LOCK SIEMPRE
            PROCESSING = False
            STOP_REQUESTED = False
            try:
                file_location.unlink(missing_ok=True)
            except Exception:
                pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )

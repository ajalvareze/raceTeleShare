import os
import uuid
from fastapi import UploadFile
from app.config import get_settings

settings = get_settings()


async def save_session_file(file: UploadFile, session_id: int) -> str:
    dest_dir = os.path.join(settings.upload_dir, "sessions", str(session_id))
    os.makedirs(dest_dir, exist_ok=True)
    ext = os.path.splitext(file.filename or "data")[1]
    filename = f"{uuid.uuid4().hex}{ext}"
    dest = os.path.join(dest_dir, filename)
    content = await file.read()
    if len(content) > settings.max_upload_size_mb * 1024 * 1024:
        raise ValueError(f"File exceeds maximum size of {settings.max_upload_size_mb} MB")
    with open(dest, "wb") as f:
        f.write(content)
    return dest


async def save_telemetry_file(file: UploadFile, lap_id: int) -> str:
    dest_dir = os.path.join(settings.upload_dir, "laps", str(lap_id))
    os.makedirs(dest_dir, exist_ok=True)
    ext = os.path.splitext(file.filename or "data")[1]
    filename = f"{uuid.uuid4().hex}{ext}"
    dest = os.path.join(dest_dir, filename)
    content = await file.read()
    if len(content) > settings.max_upload_size_mb * 1024 * 1024:
        raise ValueError(f"File exceeds maximum size of {settings.max_upload_size_mb} MB")
    with open(dest, "wb") as f:
        f.write(content)
    return dest


def delete_file(path: str) -> None:
    if path and os.path.exists(path):
        os.remove(path)

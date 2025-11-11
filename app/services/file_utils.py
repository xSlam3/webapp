"""
Утилиты для работы с файлами
"""
from fastapi import UploadFile, HTTPException
from pathlib import Path
import shutil
import os
from PIL import Image
import pillow_heif

# Папка для загрузок
UPLOAD_DIR = Path("app/static/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Разрешенные типы файлов
ALLOWED_IMAGE_TYPES = {
    "image/jpeg", 
    "image/jpg", 
    "image/png", 
    "image/gif", 
    "image/webp",
    "image/heic",      # iPhone фото
    "image/heif",      # iPhone фото (новый формат)
}
ALLOWED_VIDEO_TYPES = {
    "video/mp4", 
    "video/webm", 
    "video/mpeg",
    "video/quicktime",  # iPhone видео (.mov)
    "video/x-m4v",      # iPhone видео
}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


def save_file(file: UploadFile, file_type: str = "image") -> str:
    """
    Сохраняет файл и возвращает относительный путь для базы.
    
    Args:
        file: Загружаемый файл
        file_type: Тип файла ("image" или "video")
    
    Returns:
        Относительный путь к файлу (например, "uploads/filename.jpg")
    
    Raises:
        HTTPException: Если тип файла не разрешен
    """
    if not file or not file.filename:
        return None

    # Определяем реальный тип файла
    actual_content_type = file.content_type
    ext = Path(file.filename).suffix.lower()

    if actual_content_type == "application/octet-stream":
        if ext == ".heic":
            actual_content_type = "image/heic"
        elif ext == ".heif":
            actual_content_type = "image/heif"

    allowed_types = ALLOWED_IMAGE_TYPES if file_type == "image" else ALLOWED_VIDEO_TYPES
    if actual_content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Недопустимый тип файла: {actual_content_type}. Разрешены: {', '.join(allowed_types)}"
        )

    # Безопасное имя файла
    safe_filename = Path(file.filename).name
    file_path = UPLOAD_DIR / safe_filename
    counter = 1
    name_without_ext = file_path.stem
    extension = file_path.suffix.lower()

    while file_path.exists():
        safe_filename = f"{name_without_ext}_{counter}{extension}"
        file_path = UPLOAD_DIR / safe_filename
        counter += 1

    # Сохраняем исходный файл
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при сохранении файла: {str(e)}")

    # Конвертация HEIC → JPEG
    if extension in [".heic", ".heif"]:
        try:
            heif_file = pillow_heif.read_heif(file_path)
            image = Image.frombytes(heif_file.mode, heif_file.size, heif_file.data, "raw")

            jpeg_filename = f"{name_without_ext}.jpg"
            jpeg_path = UPLOAD_DIR / jpeg_filename

            image.save(jpeg_path, "JPEG", quality=90)
            os.remove(file_path)

            return f"uploads/{jpeg_filename}"
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Ошибка при конвертации HEIC в JPEG: {str(e)}")

    return f"uploads/{safe_filename}"

def delete_file(file_path: str) -> None:
    """
    Безопасное удаление файла

    Args:
        file_path: Относительный путь к файлу (например, "uploads/photo.jpg")
    """
    if not file_path:
        return

    try:
        full_path = Path("app/static") / file_path
        if full_path.exists() and full_path.is_file():
            os.remove(full_path)
            print(f"Deleted file: {full_path}")
    except Exception as e:
        print(f"Ошибка при удалении файла {file_path}: {e}")
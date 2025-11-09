"""
Сервис для работы с QR объектами
"""
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from app.models.qr_object_db_models import QRObject
import qrcode
from pathlib import Path
from app.config import settings
import os


def generate_qr_code(object_id: int, base_url: str = None) -> str:
    """
    Генерирует QR код для объекта
    
    Args:
        object_id: ID объекта
        base_url: Базовый URL приложения (если None, используется из настроек)
    
    Returns:
        Относительный путь к сохраненному QR коду (например, "uploads/qr_object_1.png")
    """
    # Определяем URL для QR кода
    if base_url is None:
        # Пытаемся получить из настроек или используем дефолтный
        base_url = os.getenv("BASE_URL", "http://localhost:8000")
    
    qr_url = f"{base_url}/qr/view/{object_id}"
    
    # Создаем QR код
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_url)
    qr.make(fit=True)
    
    # Создаем изображение
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Сохраняем QR код
    upload_dir = Path("app/static/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    qr_filename = f"qr_object_{object_id}.png"
    qr_path = upload_dir / qr_filename
    
    img.save(qr_path)
    
    return f"uploads/{qr_filename}"


def create_qr_object(
    name: str,
    description: Optional[str],
    photo: Optional[str],
    created_by: str,
    db: Session,
    base_url: str = None
) -> QRObject:
    """
    Создание нового QR объекта
    
    Args:
        name: Название объекта
        description: Описание объекта (HTML)
        photo: Путь к фото объекта
        created_by: Имя пользователя, создавшего объект
        db: Сессия базы данных
        base_url: Базовый URL для генерации QR кода
    
    Returns:
        QRObject: Созданный объект
    """
    # Сначала создаем объект без QR кода, чтобы получить ID
    qr_object = QRObject(
        name=name,
        description=description,
        photo=photo,
        qr_code_path="",  # Временно пустое
        created_by=created_by
    )
    db.add(qr_object)
    db.flush()  # Получаем ID без коммита
    
    # Генерируем QR код с полученным ID
    qr_code_path = generate_qr_code(qr_object.id, base_url)
    qr_object.qr_code_path = qr_code_path
    
    db.commit()
    db.refresh(qr_object)
    return qr_object


def get_qr_object_by_id(object_id: int, db: Session) -> Optional[QRObject]:
    """
    Получение QR объекта по ID
    
    Args:
        object_id: ID объекта
        db: Сессия базы данных
    
    Returns:
        Optional[QRObject]: Объект или None
    """
    return db.query(QRObject).filter(QRObject.id == object_id).first()


def get_all_qr_objects(db: Session) -> List[QRObject]:
    """
    Получение всех QR объектов
    
    Args:
        db: Сессия базы данных
    
    Returns:
        List[QRObject]: Список всех объектов
    """
    return db.query(QRObject).order_by(QRObject.created_at.desc()).all()


def update_qr_object(
    object_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    photo: Optional[str] = None,
    db: Session = None
) -> Optional[QRObject]:
    """
    Обновление QR объекта
    
    Args:
        object_id: ID объекта
        name: Новое название
        description: Новое описание
        photo: Новый путь к фото
        db: Сессия базы данных
    
    Returns:
        Optional[QRObject]: Обновленный объект или None
    """
    qr_object = db.query(QRObject).filter(QRObject.id == object_id).first()
    if not qr_object:
        return None
    
    if name is not None:
        qr_object.name = name
    if description is not None:
        qr_object.description = description
    if photo is not None:
        qr_object.photo = photo
    
    db.commit()
    db.refresh(qr_object)
    return qr_object


def delete_qr_object(object_id: int, db: Session) -> bool:
    """
    Удаление QR объекта
    
    Args:
        object_id: ID объекта
        db: Сессия базы данных
    
    Returns:
        bool: True если удален успешно
    """
    qr_object = db.query(QRObject).filter(QRObject.id == object_id).first()
    if not qr_object:
        return False
    
    # Удаляем файлы
    from app.services.file_utils import delete_file
    if qr_object.photo:
        delete_file(qr_object.photo)
    if qr_object.qr_code_path:
        delete_file(qr_object.qr_code_path)
    
    db.delete(qr_object)
    db.commit()
    return True


def qr_object_to_dict(qr_object: QRObject) -> Dict:
    """
    Преобразование QR объекта в словарь
    
    Args:
        qr_object: QR объект
    
    Returns:
        Dict: Словарь с данными объекта
    """
    return {
        "id": qr_object.id,
        "name": qr_object.name,
        "description": qr_object.description,
        "photo": qr_object.photo,
        "qr_code_path": qr_object.qr_code_path,
        "created_by": qr_object.created_by,
        "created_at": qr_object.created_at.isoformat() if qr_object.created_at else None,
        "updated_at": qr_object.updated_at.isoformat() if qr_object.updated_at else None
    }


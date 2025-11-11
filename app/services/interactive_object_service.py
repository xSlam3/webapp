"""
Сервис для работы с интерактивными объектами (AR и QR)
"""
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from app.models.interactive_object_db_models import InteractiveObject, ObjectType
from app.services.orb_service import extract_orb_features
import qrcode
from pathlib import Path
import secrets
import string


def generate_random_qr_string(length: int = 16) -> str:
    """
    Генерирует случайную строку для QR кода

    Args:
        length: Длина строки (по умолчанию 16)

    Returns:
        Случайная строка из букв и цифр
    """
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_qr_code(qr_string: str, object_id: int) -> str:
    """
    Генерирует QR код с заданной строкой

    Args:
        qr_string: Строка для кодирования в QR код
        object_id: ID объекта (для имени файла)

    Returns:
        Относительный путь к сохраненному QR коду (например, "uploads/interactive_object_1_qr.png")
    """
    # Создаем QR код
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_string)
    qr.make(fit=True)

    # Создаем изображение
    img = qr.make_image(fill_color="black", back_color="white")

    # Сохраняем QR код
    upload_dir = Path("app/static/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)

    qr_filename = f"interactive_object_{object_id}_qr.png"
    qr_path = upload_dir / qr_filename

    img.save(qr_path)

    return f"uploads/{qr_filename}"


def create_interactive_object(
    name: str,
    description: Optional[str],
    object_type: ObjectType,
    photo: Optional[str],
    recognition_image: Optional[str],  # Для AR
    created_by: str,
    db: Session
) -> InteractiveObject:
    """
    Создание нового интерактивного объекта

    Args:
        name: Название объекта
        description: Описание объекта (HTML) - это статья для отображения
        object_type: Тип объекта (AR или QR)
        photo: Путь к фото объекта для отображения
        recognition_image: Путь к изображению для распознавания (только для AR)
        created_by: Имя пользователя, создавшего объект
        db: Сессия базы данных

    Returns:
        InteractiveObject: Созданный объект
    """
    # Создаем базовый объект
    obj = InteractiveObject(
        name=name,
        description=description,
        object_type=object_type,
        photo=photo,
        recognition_image=recognition_image,
        created_by=created_by
    )

    # Специфичная обработка для AR объектов
    if object_type == ObjectType.AR:
        if not recognition_image:
            raise ValueError("AR объект требует изображение для распознавания")

        # Извлекаем ORB признаки из изображения
        orb_keypoints, orb_descriptors = extract_orb_features(recognition_image)
        obj.orb_keypoints = orb_keypoints
        obj.orb_descriptors = orb_descriptors

        # Логируем результат
        if orb_keypoints and orb_descriptors:
            print(f"AR объект '{name}' создан с ORB признаками")
        else:
            print(f"Предупреждение: AR объект '{name}' создан без ORB признаков")

    # Специфичная обработка для QR объектов
    elif object_type == ObjectType.QR:
        # Генерируем уникальную случайную строку для QR кода
        qr_string = generate_random_qr_string()

        # Проверяем уникальность
        while db.query(InteractiveObject).filter(InteractiveObject.qr_string == qr_string).first():
            qr_string = generate_random_qr_string()

        obj.qr_string = qr_string
        # QR код сгенерируем после получения ID

    # Сохраняем объект
    db.add(obj)
    db.flush()  # Получаем ID без коммита

    # Генерируем QR код для QR объектов
    if object_type == ObjectType.QR:
        qr_code_path = generate_qr_code(obj.qr_string, obj.id)
        obj.qr_code_path = qr_code_path

    db.commit()
    db.refresh(obj)
    return obj


def get_interactive_object_by_id(object_id: int, db: Session) -> Optional[InteractiveObject]:
    """
    Получение интерактивного объекта по ID

    Args:
        object_id: ID объекта
        db: Сессия базы данных

    Returns:
        Optional[InteractiveObject]: Объект или None
    """
    return db.query(InteractiveObject).filter(InteractiveObject.id == object_id).first()


def get_interactive_object_by_qr_string(qr_string: str, db: Session) -> Optional[InteractiveObject]:
    """
    Получение интерактивного объекта по строке QR кода

    Args:
        qr_string: Строка из QR кода
        db: Сессия базы данных

    Returns:
        Optional[InteractiveObject]: Объект или None
    """
    return db.query(InteractiveObject).filter(
        InteractiveObject.qr_string == qr_string,
        InteractiveObject.object_type == ObjectType.QR
    ).first()


def get_all_interactive_objects(db: Session, object_type: Optional[ObjectType] = None) -> List[InteractiveObject]:
    """
    Получение всех интерактивных объектов

    Args:
        db: Сессия базы данных
        object_type: Фильтр по типу объекта (опционально)

    Returns:
        List[InteractiveObject]: Список всех объектов
    """
    query = db.query(InteractiveObject)
    if object_type:
        query = query.filter(InteractiveObject.object_type == object_type)
    return query.order_by(InteractiveObject.created_at.desc()).all()


def get_ar_objects_for_recognition(db: Session) -> List[InteractiveObject]:
    """
    Получение всех AR объектов для распознавания

    Args:
        db: Сессия базы данных

    Returns:
        List[InteractiveObject]: Список AR объектов с ORB признаками
    """
    return db.query(InteractiveObject).filter(
        InteractiveObject.object_type == ObjectType.AR,
        InteractiveObject.orb_keypoints.isnot(None),
        InteractiveObject.orb_descriptors.isnot(None)
    ).all()


def update_interactive_object(
    object_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    photo: Optional[str] = None,
    recognition_image: Optional[str] = None,
    db: Session = None
) -> Optional[InteractiveObject]:
    """
    Обновление интерактивного объекта

    Args:
        object_id: ID объекта
        name: Новое название
        description: Новое описание
        photo: Новый путь к фото
        recognition_image: Новое изображение для распознавания (только для AR)
        db: Сессия базы данных

    Returns:
        Optional[InteractiveObject]: Обновленный объект или None
    """
    obj = db.query(InteractiveObject).filter(InteractiveObject.id == object_id).first()
    if not obj:
        return None

    if name is not None:
        obj.name = name
    if description is not None:
        obj.description = description
    if photo is not None:
        obj.photo = photo

    # Обновление изображения для распознавания (только для AR)
    if recognition_image is not None and obj.object_type == ObjectType.AR:
        obj.recognition_image = recognition_image
        # Пересчитываем ORB признаки
        orb_keypoints, orb_descriptors = extract_orb_features(recognition_image)
        obj.orb_keypoints = orb_keypoints
        obj.orb_descriptors = orb_descriptors

    db.commit()
    db.refresh(obj)
    return obj


def delete_interactive_object(object_id: int, db: Session) -> bool:
    """
    Удаление интерактивного объекта

    Args:
        object_id: ID объекта
        db: Сессия базы данных

    Returns:
        bool: True если удален успешно
    """
    obj = db.query(InteractiveObject).filter(InteractiveObject.id == object_id).first()
    if not obj:
        return False

    # Удаляем файлы
    from app.services.file_utils import delete_file
    if obj.photo:
        delete_file(obj.photo)
    if obj.recognition_image:
        delete_file(obj.recognition_image)
    if obj.qr_code_path:
        delete_file(obj.qr_code_path)

    db.delete(obj)
    db.commit()
    return True


def interactive_object_to_dict(obj: InteractiveObject) -> Dict:
    """
    Преобразование интерактивного объекта в словарь

    Args:
        obj: Интерактивный объект

    Returns:
        Dict: Словарь с данными объекта
    """
    return {
        "id": obj.id,
        "name": obj.name,
        "description": obj.description,
        "object_type": obj.object_type.value,
        "photo": obj.photo,
        "recognition_image": obj.recognition_image,
        "qr_code_path": obj.qr_code_path,
        "qr_string": obj.qr_string,
        "created_by": obj.created_by,
        "created_at": obj.created_at.isoformat() if obj.created_at else None,
        "updated_at": obj.updated_at.isoformat() if obj.updated_at else None
    }

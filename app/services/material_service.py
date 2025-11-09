"""
Сервис для работы с материалами в БД
"""
from sqlalchemy.orm import Session
from app.models.material_db_models import Material
from typing import Optional, List


def create_material(db: Session, title: str, text: Optional[str] = None, 
                   photo: Optional[str] = None, video: Optional[str] = None,
                   created_by: Optional[str] = None) -> Material:
    """
    Создать новый материал
    
    Args:
        db: Сессия базы данных
        title: Заголовок материала
        text: Текст материала
        photo: Путь к фото
        video: Путь к видео
        created_by: Имя создателя
    
    Returns:
        Material: Созданный материал
    """
    material = Material(
        title=title,
        text=text,
        photo=photo,
        video=video,
        created_by=created_by
    )
    db.add(material)
    db.commit()
    db.refresh(material)
    return material


def get_material_by_id(db: Session, material_id: int) -> Optional[Material]:
    """
    Получить материал по ID
    
    Args:
        db: Сессия базы данных
        material_id: ID материала
    
    Returns:
        Optional[Material]: Материал или None
    """
    return db.query(Material).filter(Material.id == material_id).first()


def get_all_materials(db: Session, skip: int = 0, limit: int = 100) -> List[Material]:
    """
    Получить все материалы
    
    Args:
        db: Сессия базы данных
        skip: Количество пропущенных записей
        limit: Максимальное количество записей
    
    Returns:
        List[Material]: Список материалов
    """
    return db.query(Material).offset(skip).limit(limit).all()


def update_material(db: Session, material: Material, **kwargs) -> Material:
    """
    Обновить материал
    
    Args:
        db: Сессия базы данных
        material: Материал для обновления
        **kwargs: Поля для обновления
    
    Returns:
        Material: Обновленный материал
    """
    for key, value in kwargs.items():
        if value is not None or key in ['photo', 'video']:  # Разрешаем установку None для фото/видео
            setattr(material, key, value)
    db.commit()
    db.refresh(material)
    return material


def delete_material(db: Session, material: Material) -> bool:
    """
    Удалить материал
    
    Args:
        db: Сессия базы данных
        material: Материал для удаления
    
    Returns:
        bool: True если удаление успешно
    """
    db.delete(material)
    db.commit()
    return True


def search_materials(db: Session, query: str) -> List[Material]:
    """
    Поиск материалов по заголовку и тексту
    
    Args:
        db: Сессия базы данных
        query: Поисковый запрос
    
    Returns:
        List[Material]: Список найденных материалов
    """
    search_term = f"%{query.lower()}%"
    return db.query(Material).filter(
        (Material.title.ilike(search_term)) | 
        (Material.text.ilike(search_term))
    ).all()


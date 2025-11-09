"""
Утилиты для работы с материалами базы знаний (обертка для БД)
"""
from sqlalchemy.orm import Session
from app.services.material_service import (
    create_material as db_create_material,
    get_material_by_id as db_get_material_by_id,
    get_all_materials as db_get_all_materials,
    update_material as db_update_material,
    delete_material as db_delete_material,
    search_materials as db_search_materials
)
from app.models.material_models import Material


def create_material(material: Material, db: Session, created_by: str = None) -> Material:
    """
    Создает новый материал с автоматически сгенерированным ID
    
    Args:
        material: Модель материала
        db: Сессия базы данных
        created_by: Имя создателя
    
    Returns:
        Material: Созданный материал
    """
    db_material = db_create_material(
        db=db,
        title=material.title,
        text=material.text,
        photo=material.photo,
        video=material.video,
        created_by=created_by
    )
    
    # Конвертируем в Pydantic модель
    return Material(
        id=db_material.id,
        title=db_material.title,
        text=db_material.text,
        photo=db_material.photo,
        video=db_material.video,
        created_by=db_material.created_by,
        created_at=db_material.created_at,
        updated_at=db_material.updated_at
    )


def read_materials(db: Session):
    """
    Возвращает все материалы
    
    Args:
        db: Сессия базы данных
    
    Returns:
        List[dict]: Список материалов в виде словарей
    """
    db_materials = db_get_all_materials(db)
    return [
        {
            "id": m.id,
            "title": m.title,
            "text": m.text,
            "photo": m.photo,
            "video": m.video,
            "created_by": m.created_by,
            "created_at": m.created_at.isoformat() if m.created_at else None,
            "updated_at": m.updated_at.isoformat() if m.updated_at else None
        }
        for m in db_materials
    ]


def read_material_by_id(material_id: int, db: Session):
    """
    Находит материал по ID
    
    Args:
        material_id: ID материала
        db: Сессия базы данных
    
    Returns:
        Optional[dict]: Материал в виде словаря или None
    """
    db_material = db_get_material_by_id(db, material_id)
    if not db_material:
        return None
    
    return {
        "id": db_material.id,
        "title": db_material.title,
        "text": db_material.text,
        "photo": db_material.photo,
        "video": db_material.video,
        "created_by": db_material.created_by,
        "created_at": db_material.created_at.isoformat() if db_material.created_at else None,
        "updated_at": db_material.updated_at.isoformat() if db_material.updated_at else None
    }


def update_material(material_id: int, updated_data: dict, db: Session):
    """
    Обновляет материал по ID
    
    Args:
        material_id: ID материала
        updated_data: Данные для обновления
        db: Сессия базы данных
    
    Returns:
        Optional[dict]: Обновленный материал в виде словаря или None
    """
    db_material = db_get_material_by_id(db, material_id)
    if not db_material:
        return None
    
    db_update_material(db, db_material, **updated_data)
    
    return {
        "id": db_material.id,
        "title": db_material.title,
        "text": db_material.text,
        "photo": db_material.photo,
        "video": db_material.video,
        "created_by": db_material.created_by,
        "created_at": db_material.created_at.isoformat() if db_material.created_at else None,
        "updated_at": db_material.updated_at.isoformat() if db_material.updated_at else None
    }


def delete_material(material_id: int, db: Session):
    """
    Удаляет материал по ID
    
    Args:
        material_id: ID материала
        db: Сессия базы данных
    
    Returns:
        Optional[dict]: Словарь с ID удаленного материала или None
    """
    db_material = db_get_material_by_id(db, material_id)
    if not db_material:
        return None
    
    db_delete_material(db, db_material)
    return {"id": material_id}

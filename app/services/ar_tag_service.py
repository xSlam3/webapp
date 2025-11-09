"""
Сервис для работы с AR тегами
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional, Dict
from app.models.ar_tag_db_models import ARTag
from app.models.material_db_models import Material


def create_ar_tag(
    name: str,
    description: Optional[str],
    tag_image: str,
    material_id: int,
    created_by: str,
    db: Session
) -> ARTag:
    """Создание нового AR тега"""
    # Проверяем существование материала
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        raise ValueError(f"Материал с ID {material_id} не найден")
    
    ar_tag = ARTag(
        name=name,
        description=description,
        tag_image=tag_image,
        material_id=material_id,
        created_by=created_by
    )
    db.add(ar_tag)
    db.commit()
    db.refresh(ar_tag)
    return ar_tag


def get_ar_tag_by_id(tag_id: int, db: Session) -> Optional[ARTag]:
    """Получение AR тега по ID"""
    return db.query(ARTag).filter(ARTag.id == tag_id).first()


def get_ar_tag_by_material_id(material_id: int, db: Session) -> Optional[ARTag]:
    """Получение AR тега по ID материала"""
    return db.query(ARTag).filter(ARTag.material_id == material_id).first()


def get_all_ar_tags(db: Session) -> List[ARTag]:
    """Получение всех AR тегов"""
    return db.query(ARTag).order_by(ARTag.created_at.desc()).all()


def update_ar_tag(
    tag_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    tag_image: Optional[str] = None,
    material_id: Optional[int] = None,
    db: Session = None
) -> Optional[ARTag]:
    """Обновление AR тега"""
    ar_tag = db.query(ARTag).filter(ARTag.id == tag_id).first()
    if not ar_tag:
        return None
    
    if name is not None:
        ar_tag.name = name
    if description is not None:
        ar_tag.description = description
    if tag_image is not None:
        ar_tag.tag_image = tag_image
    if material_id is not None:
        # Проверяем существование материала
        material = db.query(Material).filter(Material.id == material_id).first()
        if not material:
            raise ValueError(f"Материал с ID {material_id} не найден")
        ar_tag.material_id = material_id
    
    db.commit()
    db.refresh(ar_tag)
    return ar_tag


def delete_ar_tag(tag_id: int, db: Session) -> bool:
    """Удаление AR тега"""
    ar_tag = db.query(ARTag).filter(ARTag.id == tag_id).first()
    if not ar_tag:
        return False
    
    db.delete(ar_tag)
    db.commit()
    return True


def ar_tag_to_dict(ar_tag: ARTag, db: Session, include_material: bool = False) -> Dict:
    """Преобразование AR тега в словарь"""
    result = {
        "id": ar_tag.id,
        "name": ar_tag.name,
        "description": ar_tag.description,
        "tag_image": ar_tag.tag_image,
        "material_id": ar_tag.material_id,
        "created_by": ar_tag.created_by,
        "created_at": ar_tag.created_at.isoformat() if ar_tag.created_at else None,
        "updated_at": ar_tag.updated_at.isoformat() if ar_tag.updated_at else None
    }
    
    if include_material:
        material = db.query(Material).filter(Material.id == ar_tag.material_id).first()
        if material:
            result["material"] = {
                "id": material.id,
                "title": material.title,
                "text": material.text,
                "photo": material.photo,
                "video": material.video
            }
    
    return result


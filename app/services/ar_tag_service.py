"""
Service for working with AR tags
"""
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from app.models.ar_tag_db_models import ARTag
from app.models.article_db_models import Article
from app.services.orb_service import extract_orb_features


def create_ar_tag(
    name: str,
    description: Optional[str],
    tag_image: str,
    article_id: Optional[int],
    created_by: str,
    db: Session
) -> ARTag:
    """Create new AR tag"""
    # Check if article exists (if specified)
    if article_id is not None:
        article = db.query(Article).filter(Article.id == article_id).first()
        if not article:
            raise ValueError(f"Article with ID {article_id} not found")

    # Извлекаем ORB признаки из изображения тега
    orb_keypoints, orb_descriptors = extract_orb_features(tag_image)

    ar_tag = ARTag(
        name=name,
        description=description,
        tag_image=tag_image,
        article_id=article_id,
        created_by=created_by,
        orb_keypoints=orb_keypoints,
        orb_descriptors=orb_descriptors
    )
    db.add(ar_tag)
    db.commit()
    db.refresh(ar_tag)

    # Log feature extraction result
    if orb_keypoints and orb_descriptors:
        print(f"AR tag '{name}' created with ORB features")
    else:
        print(f"Warning: AR tag '{name}' created without ORB features")

    return ar_tag


def get_ar_tag_by_id(tag_id: int, db: Session) -> Optional[ARTag]:
    """Get AR tag by ID"""
    return db.query(ARTag).filter(ARTag.id == tag_id).first()


def get_ar_tag_by_article_id(article_id: int, db: Session) -> Optional[ARTag]:
    """Get AR tag by article ID"""
    return db.query(ARTag).filter(ARTag.article_id == article_id).first()


def get_all_ar_tags(db: Session) -> List[ARTag]:
    """Получение всех AR тегов"""
    return db.query(ARTag).order_by(ARTag.created_at.desc()).all()


def update_ar_tag(
    tag_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    tag_image: Optional[str] = None,
    article_id: Optional[int] = None,
    db: Session = None
) -> Optional[ARTag]:
    """Update AR tag"""
    ar_tag = db.query(ARTag).filter(ARTag.id == tag_id).first()
    if not ar_tag:
        return None

    if name is not None:
        ar_tag.name = name
    if description is not None:
        ar_tag.description = description
    if tag_image is not None:
        ar_tag.tag_image = tag_image
    if article_id is not None:
        # Check if article exists
        article = db.query(Article).filter(Article.id == article_id).first()
        if not article:
            raise ValueError(f"Article with ID {article_id} not found")
        ar_tag.article_id = article_id

    db.commit()
    db.refresh(ar_tag)
    return ar_tag


def delete_ar_tag(tag_id: int, db: Session) -> bool:
    """Delete AR tag"""
    ar_tag = db.query(ARTag).filter(ARTag.id == tag_id).first()
    if not ar_tag:
        return False

    db.delete(ar_tag)
    db.commit()
    return True


def ar_tag_to_dict(ar_tag: ARTag, db: Session, include_article: bool = False) -> Dict:
    """Convert AR tag to dictionary"""
    result = {
        "id": ar_tag.id,
        "name": ar_tag.name,
        "description": ar_tag.description,
        "tag_image": ar_tag.tag_image,
        "article_id": ar_tag.article_id,
        "created_by": ar_tag.created_by,
        "created_at": ar_tag.created_at.isoformat() if ar_tag.created_at else None,
        "updated_at": ar_tag.updated_at.isoformat() if ar_tag.updated_at else None
    }

    if include_article:
        article = db.query(Article).filter(Article.id == ar_tag.article_id).first()
        if article:
            result["article"] = {
                "id": article.id,
                "title": article.title,
                "text": article.text,
                "photo": article.photo,
                "video": article.video
            }

    return result


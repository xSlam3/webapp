"""
Utilities for working with knowledge base articles (wrapper for DB)
"""
from sqlalchemy.orm import Session
from app.services.article_service import (
    create_article as db_create_article,
    get_article_by_id as db_get_article_by_id,
    get_all_articles as db_get_all_articles,
    update_article as db_update_article,
    delete_article as db_delete_article,
    search_articles as db_search_articles
)
from app.models.article_models import Article


def create_article(article: Article, db: Session, created_by: str = None) -> Article:
    """
    Creates a new article with auto-generated ID

    Args:
        article: Article model
        db: Database session
        created_by: Creator username

    Returns:
        Article: Created article
    """
    db_article = db_create_article(
        db=db,
        title=article.title,
        text=article.text,
        photo=article.photo,
        video=article.video,
        created_by=created_by
    )

    # Convert to Pydantic model
    return Article(
        id=db_article.id,
        title=db_article.title,
        text=db_article.text,
        photo=db_article.photo,
        video=db_article.video,
        created_by=db_article.created_by,
        created_at=db_article.created_at,
        updated_at=db_article.updated_at
    )


def read_articles(db: Session):
    """
    Returns all articles

    Args:
        db: Database session

    Returns:
        List[dict]: List of articles as dictionaries
    """
    db_articles = db_get_all_articles(db)
    return [
        {
            "id": a.id,
            "title": a.title,
            "text": a.text,
            "photo": a.photo,
            "video": a.video,
            "created_by": a.created_by,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "updated_at": a.updated_at.isoformat() if a.updated_at else None
        }
        for a in db_articles
    ]


def read_article_by_id(article_id: int, db: Session):
    """
    Finds article by ID

    Args:
        article_id: Article ID
        db: Database session

    Returns:
        Optional[dict]: Article as dictionary or None
    """
    db_article = db_get_article_by_id(db, article_id)
    if not db_article:
        return None

    return {
        "id": db_article.id,
        "title": db_article.title,
        "text": db_article.text,
        "photo": db_article.photo,
        "video": db_article.video,
        "created_by": db_article.created_by,
        "created_at": db_article.created_at.isoformat() if db_article.created_at else None,
        "updated_at": db_article.updated_at.isoformat() if db_article.updated_at else None
    }


def update_article(article_id: int, updated_data: dict, db: Session):
    """
    Updates article by ID

    Args:
        article_id: Article ID
        updated_data: Data to update
        db: Database session

    Returns:
        Optional[dict]: Updated article as dictionary or None
    """
    db_article = db_get_article_by_id(db, article_id)
    if not db_article:
        return None

    db_update_article(db, db_article, **updated_data)

    return {
        "id": db_article.id,
        "title": db_article.title,
        "text": db_article.text,
        "photo": db_article.photo,
        "video": db_article.video,
        "created_by": db_article.created_by,
        "created_at": db_article.created_at.isoformat() if db_article.created_at else None,
        "updated_at": db_article.updated_at.isoformat() if db_article.updated_at else None
    }


def delete_article(article_id: int, db: Session):
    """
    Deletes article by ID

    Args:
        article_id: Article ID
        db: Database session

    Returns:
        Optional[dict]: Dictionary with deleted article ID or None
    """
    db_article = db_get_article_by_id(db, article_id)
    if not db_article:
        return None

    db_delete_article(db, db_article)
    return {"id": article_id}

"""
Service for working with knowledge base articles in database
"""
from sqlalchemy.orm import Session
from app.models.article_db_models import Article
from app.services.embedding_service import (
    generate_article_embedding,
    generate_embedding,
    embedding_from_json,
    cosine_similarity
)
from typing import Optional, List, Tuple
import logging

logger = logging.getLogger(__name__)


def create_article(db: Session, title: str, text: Optional[str] = None,
                   photo: Optional[str] = None, video: Optional[str] = None,
                   created_by: Optional[str] = None) -> Article:
    """
    Create a new article

    Args:
        db: Database session
        title: Article title
        text: Article text content
        photo: Path to photo
        video: Path to video
        created_by: Creator username

    Returns:
        Article: Created article
    """
    # Generate embedding for new article
    embedding = generate_article_embedding(title, text)

    article = Article(
        title=title,
        text=text,
        photo=photo,
        video=video,
        created_by=created_by,
        embedding=embedding
    )
    db.add(article)
    db.commit()
    db.refresh(article)
    return article


def get_article_by_id(db: Session, article_id: int) -> Optional[Article]:
    """
    Get article by ID

    Args:
        db: Database session
        article_id: Article ID

    Returns:
        Optional[Article]: Article or None
    """
    return db.query(Article).filter(Article.id == article_id).first()


def get_all_articles(db: Session, skip: int = 0, limit: int = 100) -> List[Article]:
    """
    Get all articles

    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records

    Returns:
        List[Article]: List of articles
    """
    return db.query(Article).offset(skip).limit(limit).all()


def update_article(db: Session, article: Article, **kwargs) -> Article:
    """
    Update article

    Args:
        db: Database session
        article: Article to update
        **kwargs: Fields to update

    Returns:
        Article: Updated article
    """
    # Check if title or text changed - need to regenerate embedding
    regenerate_embedding = False
    if 'title' in kwargs or 'text' in kwargs:
        regenerate_embedding = True

    for key, value in kwargs.items():
        if value is not None or key in ['photo', 'video']:  # Allow setting None for photo/video
            setattr(article, key, value)

    # Regenerate embedding if content changed
    if regenerate_embedding:
        new_embedding = generate_article_embedding(article.title, article.text)
        article.embedding = new_embedding

    db.commit()
    db.refresh(article)
    return article


def delete_article(db: Session, article: Article) -> bool:
    """
    Delete article

    Args:
        db: Database session
        article: Article to delete

    Returns:
        bool: True if deletion successful
    """
    db.delete(article)
    db.commit()
    return True


def search_articles(db: Session, query: str) -> List[Article]:
    """
    Search articles by title and text (simple text search)

    Args:
        db: Database session
        query: Search query

    Returns:
        List[Article]: List of found articles
    """
    search_term = f"%{query.lower()}%"
    return db.query(Article).filter(
        (Article.title.ilike(search_term)) |
        (Article.text.ilike(search_term))
    ).all()


def semantic_search_articles(db: Session, query: str, limit: int = 10, threshold: float = 0.3) -> List[Article]:
    """
    Semantic search of articles by vector similarity

    Args:
        db: Database session
        query: Search query
        limit: Maximum number of results
        threshold: Minimum similarity threshold (0-1)

    Returns:
        List[Article]: List of articles sorted by relevance
    """
    try:
        # Generate embedding for search query
        query_embedding = generate_embedding(query)
        if not query_embedding:
            logger.warning("Failed to create embedding for query, using regular search")
            return search_articles(db, query)[:limit]

        # Get all articles with embeddings
        all_articles = db.query(Article).filter(Article.embedding.isnot(None)).all()

        if not all_articles:
            logger.warning("No articles with embeddings in DB, using regular search")
            return search_articles(db, query)[:limit]

        # Calculate similarity for each article
        articles_with_similarity: List[Tuple[Article, float]] = []

        import numpy as np
        query_emb_array = np.array(query_embedding)

        for article in all_articles:
            if article.embedding:
                article_emb_array = embedding_from_json(article.embedding)
                if article_emb_array is not None:
                    similarity = cosine_similarity(query_emb_array, article_emb_array)
                    if similarity >= threshold:
                        articles_with_similarity.append((article, similarity))

        # Sort by descending similarity
        articles_with_similarity.sort(key=lambda x: x[1], reverse=True)

        # Return top results
        result = [article for article, _ in articles_with_similarity[:limit]]

        logger.info(f"Semantic search: found {len(result)} articles for query '{query}'")
        return result

    except Exception as e:
        logger.error(f"Error during semantic search: {e}")
        # In case of error, return regular search results
        return search_articles(db, query)[:limit]


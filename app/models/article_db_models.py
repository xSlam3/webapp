"""
SQLAlchemy models for knowledge base articles
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from app.database import Base


class Article(Base):
    """Article model in database"""
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False, index=True)
    text = Column(String(10000), nullable=True)
    photo = Column(String(500), nullable=True)
    video = Column(String(500), nullable=True)
    created_by = Column(String(50), ForeignKey("users.username"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    embedding = Column(Text, nullable=True)  # JSON array of vector representation

    # Relationship with user (optional, without relationship for simplicity)

    def __repr__(self):
        return f"<Article(id={self.id}, title='{self.title[:30]}...')>"


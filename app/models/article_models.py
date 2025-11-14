"""
Pydantic models for knowledge base articles
"""
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from typing import Optional


class ArticleBase(BaseModel):
    """Base article model"""
    title: str = Field(..., min_length=2, max_length=200)
    text: Optional[str] = Field(None, max_length=10000)

    @field_validator('title')
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        """Validate that title is not empty"""
        if not v or not v.strip():
            raise ValueError('Title cannot be empty')
        return v.strip()

    @field_validator('text')
    @classmethod
    def text_cleanup(cls, v: Optional[str]) -> Optional[str]:
        """Clean up text content"""
        if v:
            return v.strip() if v.strip() else None
        return None


class ArticleCreate(ArticleBase):
    """Model for creating an article"""
    pass


class ArticleUpdate(BaseModel):
    """Model for updating an article (all fields optional)"""
    title: Optional[str] = Field(None, min_length=2, max_length=200)
    text: Optional[str] = Field(None, max_length=10000)
    photo: Optional[str] = None
    video: Optional[str] = None

    @field_validator('title')
    @classmethod
    def title_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and (not v or not v.strip()):
            raise ValueError('Title cannot be empty')
        return v.strip() if v else None


class Article(ArticleBase):
    """Complete article model"""
    id: int
    photo: Optional[str] = None
    video: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None  # username of creator

    class Config:
        from_attributes = True


class ArticleResponse(Article):
    """Model for API responses"""
    pass


class ArticleListResponse(BaseModel):
    """Model for article list responses"""
    articles: list[ArticleResponse]
    total: int


class MessageResponse(BaseModel):
    """Стандартный ответ с сообщением"""
    success: bool
    message: str
    detail: Optional[str] = None
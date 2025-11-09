"""
Pydantic модели для материалов базы знаний
"""
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from typing import Optional


class MaterialBase(BaseModel):
    """Базовая модель материала"""
    title: str = Field(..., min_length=2, max_length=200)
    text: Optional[str] = Field(None, max_length=10000)
    
    @field_validator('title')
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        """Проверка, что заголовок не пустой"""
        if not v or not v.strip():
            raise ValueError('Заголовок не может быть пустым')
        return v.strip()
    
    @field_validator('text')
    @classmethod
    def text_cleanup(cls, v: Optional[str]) -> Optional[str]:
        """Очистка текста"""
        if v:
            return v.strip() if v.strip() else None
        return None


class MaterialCreate(MaterialBase):
    """Модель для создания материала"""
    pass


class MaterialUpdate(BaseModel):
    """Модель для обновления материала (все поля опциональны)"""
    title: Optional[str] = Field(None, min_length=2, max_length=200)
    text: Optional[str] = Field(None, max_length=10000)
    photo: Optional[str] = None
    video: Optional[str] = None
    
    @field_validator('title')
    @classmethod
    def title_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and (not v or not v.strip()):
            raise ValueError('Заголовок не может быть пустым')
        return v.strip() if v else None


class Material(MaterialBase):
    """Полная модель материала"""
    id: int
    photo: Optional[str] = None
    video: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None  # username создателя
    
    class Config:
        from_attributes = True


class MaterialResponse(Material):
    """Модель для ответов API"""
    pass


class MaterialListResponse(BaseModel):
    """Модель для списка материалов"""
    materials: list[MaterialResponse]
    total: int


class MessageResponse(BaseModel):
    """Стандартный ответ с сообщением"""
    success: bool
    message: str
    detail: Optional[str] = None
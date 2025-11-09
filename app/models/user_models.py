"""
Pydantic модели для аутентификации и пользователей
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    """Базовая модель пользователя"""
    username: str = Field(..., min_length=3, max_length=50)


class UserCreate(UserBase):
    """Модель для создания пользователя"""
    password: str = Field(..., min_length=6, max_length=100)
    
    @field_validator('username')
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        """Валидация username - только буквы и цифры"""
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Имя пользователя может содержать только буквы, цифры, _ и -')
        return v.lower()
    
    @field_validator('password')
    @classmethod
    def password_strength(cls, v: str) -> str:
        """Проверка надёжности пароля"""
        if len(v) < 6:
            raise ValueError('Пароль должен содержать минимум 6 символов')
        return v


class UserUpdate(BaseModel):
    """Модель для обновления пользователя"""
    password: Optional[str] = Field(None, min_length=6, max_length=100)
    is_admin: Optional[bool] = None


class UserInDB(UserBase):
    """Модель пользователя в БД"""
    hashed_password: str
    is_admin: bool = False
    created_at: datetime = Field(default_factory=datetime.now)
    is_active: bool = True


class UserResponse(UserBase):
    """Модель пользователя для ответов API (без пароля)"""
    is_admin: bool = False
    is_active: bool = True
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """Модель для списка пользователей"""
    users: list[UserResponse]
    total: int


class TokenResponse(BaseModel):
    """Модель ответа с токеном"""
    access_token: str
    token_type: str = "bearer"


class MessageResponse(BaseModel):
    """Стандартный ответ с сообщением"""
    success: bool
    message: str
    detail: Optional[str] = None


class LoginRequest(BaseModel):
    """Модель для логина (альтернатива Form)"""
    username: str
    password: str
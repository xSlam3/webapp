"""
Сервис для работы с пользователями в БД
"""
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.user_db_models import User
from app.services.auth import get_password_hash, verify_password
from typing import Optional


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """
    Получить пользователя по username
    
    Args:
        db: Сессия базы данных
        username: Имя пользователя
    
    Returns:
        Optional[User]: Пользователь или None
    """
    return db.query(User).filter(User.username == username.lower()).first()


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """
    Получить пользователя по ID
    
    Args:
        db: Сессия базы данных
        user_id: ID пользователя
    
    Returns:
        Optional[User]: Пользователь или None
    """
    return db.query(User).filter(User.id == user_id).first()


def create_user(db: Session, username: str, password: str, is_admin: bool = False) -> User:
    """
    Создать нового пользователя
    
    Args:
        db: Сессия базы данных
        username: Имя пользователя
        password: Пароль
        is_admin: Флаг администратора
    
    Returns:
        User: Созданный пользователь
    
    Raises:
        ValueError: Если пользователь с таким именем уже существует
    """
    hashed_password = get_password_hash(password)
    user = User(
        username=username.lower(),
        hashed_password=hashed_password,
        is_admin=is_admin,
        is_active=True
    )
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
        return user
    except IntegrityError:
        db.rollback()
        raise ValueError("Пользователь с таким именем уже существует")


def verify_user_password(user: User, password: str) -> bool:
    """
    Проверить пароль пользователя
    
    Args:
        user: Пользователь
        password: Пароль для проверки
    
    Returns:
        bool: True если пароль верный
    """
    return verify_password(password, user.hashed_password)


def get_all_users(db: Session, skip: int = 0, limit: int = 100):
    """
    Получить всех пользователей
    
    Args:
        db: Сессия базы данных
        skip: Количество пропущенных записей
        limit: Максимальное количество записей
    
    Returns:
        List[User]: Список пользователей
    """
    return db.query(User).offset(skip).limit(limit).all()


def update_user(db: Session, user: User, **kwargs) -> User:
    """
    Обновить пользователя
    
    Args:
        db: Сессия базы данных
        user: Пользователь для обновления
        **kwargs: Поля для обновления
    
    Returns:
        User: Обновленный пользователь
    """
    for key, value in kwargs.items():
        if value is not None:
            # Если обновляется пароль, нужно его захешировать
            if key == "password":
                user.hashed_password = get_password_hash(value)
            else:
                setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user: User) -> bool:
    """
    Удалить пользователя
    
    Args:
        db: Сессия базы данных
        user: Пользователь для удаления
    
    Returns:
        bool: True если удаление успешно
    """
    db.delete(user)
    db.commit()
    return True


def toggle_user_status(db: Session, user: User) -> User:
    """
    Переключить статус активности пользователя
    
    Args:
        db: Сессия базы данных
        user: Пользователь
    
    Returns:
        User: Обновленный пользователь
    """
    user.is_active = not user.is_active
    db.commit()
    db.refresh(user)
    return user


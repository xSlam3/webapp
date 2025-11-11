"""
Утилиты для работы с JWT токенами и паролями
"""
from datetime import datetime, timedelta
from typing import Optional, Annotated
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Cookie, Request
from app.config import settings

# Контекст для хеширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Проверка пароля
    
    Args:
        plain_password: Пароль в открытом виде
        hashed_password: Хешированный пароль
        
    Returns:
        True если пароли совпадают
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Хеширование пароля
    
    Args:
        password: Пароль в открытом виде
        
    Returns:
        Хешированный пароль
    """
    return pwd_context.hash(password)


def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    """
    Создание JWT токена
    
    Args:
        subject: Идентификатор пользователя (обычно username)
        expires_delta: Время жизни токена
        
    Returns:
        JWT токен
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.utcnow()
    }
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """
    Декодирование JWT токена
    
    Args:
        token: JWT токен
        
    Returns:
        Payload токена или None
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


def get_current_user(
    request: Request,
    access_token: Annotated[Optional[str], Cookie()] = None
) -> dict:
    """
    Получение текущего пользователя из токена

    Args:
        request: HTTP запрос (для определения типа ответа)
        access_token: JWT токен из cookie

    Returns:
        Данные пользователя

    Raises:
        HTTPException: Если токен невалидный или отсутствует
    """
    # Сохраняем информацию о типе запроса в request.state для exception handler
    is_api_request = (
        request.url.path.startswith("/api/") or
        "application/json" in request.headers.get("accept", "").lower() or
        request.headers.get("content-type", "").lower() == "application/json"
    )
    request.state.is_api_request = is_api_request
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось проверить учетные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not access_token:
        raise credentials_exception
    
    # Удаляем префикс "Bearer " если он есть
    token = access_token.replace("Bearer ", "")
    
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    
    username: str = payload.get("sub")
    if username is None:
        raise credentials_exception
    
    # Возвращаем username (проверка в БД будет в роутерах)
    return {"username": username}


def get_current_user_optional(
    access_token: Annotated[Optional[str], Cookie()] = None
) -> Optional[dict]:
    """
    Получение текущего пользователя из токена (опционально, не выбрасывает исключение)

    Args:
        access_token: JWT токен из cookie

    Returns:
        Данные пользователя или None если не авторизован
    """
    if not access_token:
        return None
    
    try:
        # Удаляем префикс "Bearer " если он есть
        token = access_token.replace("Bearer ", "")
        
        payload = decode_access_token(token)
        if payload is None:
            return None
        
        username: str = payload.get("sub")
        if username is None:
            return None
        
        # Возвращаем username (проверка в БД будет в роутерах)
        return {"username": username}
    except Exception:
        return None
"""
Роутер аутентификации с поддержкой БД
"""
from fastapi import APIRouter, Depends, HTTPException, status, Form, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from datetime import timedelta
from typing import Optional
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.auth import (
    create_access_token,
    get_current_user,
    get_current_user_optional
)
from app.services.user_service import (
    get_user_by_username,
    create_user,
    verify_user_password,
    get_all_users,
    delete_user as delete_user_service,
    toggle_user_status,
    update_user
)
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["auth"])
templates = Jinja2Templates(directory="app/templates")


# -----------------------------------------------------------------------------
# Вспомогательные функции
# -----------------------------------------------------------------------------

def get_current_admin_user(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Проверка прав администратора
    
    Args:
        current_user: Текущий пользователь
        db: Сессия базы данных
    
    Returns:
        dict: Данные пользователя-администратора
    
    Raises:
        HTTPException: Если пользователь не администратор
    """
    user = get_user_by_username(db, current_user["username"])
    if not user or not user.is_active or not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только администраторы могут выполнять это действие"
        )
    return current_user


# -----------------------------------------------------------------------------
# HTML страницы
# -----------------------------------------------------------------------------

@router.get("/", response_class=HTMLResponse, name="auth_page")
def auth_form(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    Форма логина и регистрации
    
    Args:
        request: HTTP запрос
        db: Сессия базы данных
        current_user: Текущий пользователь (опционально)
    
    Returns:
        HTMLResponse: HTML страница авторизации
    """
    # Получаем полную информацию о пользователе для шаблона
    user_info = None
    if current_user:
        user = get_user_by_username(db, current_user.get("username"))
        if user and user.is_active:
            user_info = {
                "username": user.username,
                "is_admin": user.is_admin
            }
    
    return templates.TemplateResponse(
        "auth.html", 
        {
            "request": request,
            "current_user": user_info
        }
    )


@router.get("/admin", response_class=HTMLResponse, name="admin_page")
def admin_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user)
):
    """
    Страница админ-панели (только для админов)
    
    Args:
        request: HTTP запрос
        db: Сессия базы данных
        current_user: Текущий пользователь-администратор
    
    Returns:
        HTMLResponse: HTML страница админ-панели
    
    Raises:
        HTTPException: Если пользователь не администратор
    """
    user = get_user_by_username(db, current_user.get("username"))
    user_info = {
        "username": user.username,
        "is_admin": user.is_admin
    }
    
    return templates.TemplateResponse(
        "admin.html", 
        {
            "request": request,
            "current_user": user_info
        }
    )


@router.get("/profile", response_class=HTMLResponse, name="profile_page")
def profile_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    Страница профиля пользователя
    
    Args:
        request: HTTP запрос
        db: Сессия базы данных
        current_user: Текущий пользователь (опционально)
    
    Returns:
        HTMLResponse: HTML страница профиля или редирект на /auth/
    """
    if not current_user:
        return RedirectResponse(url="/auth/")
    
    user = get_user_by_username(db, current_user.get("username"))
    if not user:
        return RedirectResponse(url="/auth/")
    
    user_info = {
        "username": user.username,
        "is_admin": user.is_admin,
        "is_active": user.is_active
    }
    
    return templates.TemplateResponse(
        "profile.html",
        {
            "request": request,
            "current_user": user_info
        }
    )


# -----------------------------------------------------------------------------
# API endpoints
# -----------------------------------------------------------------------------

@router.post("/admin/create-user")
def create_user_by_admin(
    username: str = Form(...),
    password: str = Form(...),
    is_admin: bool = Form(False),
    admin: dict = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Создание нового пользователя администратором (только для админов)

    Args:
        username: Имя пользователя
        password: Пароль
        is_admin: Является ли пользователь администратором
        admin: Текущий пользователь-администратор
        db: Сессия базы данных

    Returns:
        JSONResponse: JSON с результатом создания

    Raises:
        HTTPException: Если валидация не пройдена, пользователь уже существует или текущий пользователь не администратор
    """
    # Валидация
    if not username or len(username.strip()) < 3:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Имя пользователя должно содержать минимум 3 символа"
        )

    if not password or len(password) < 6:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Пароль должен содержать минимум 6 символов"
        )

    username = username.strip().lower()

    # Проверка существования
    existing_user = get_user_by_username(db, username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким именем уже существует"
        )

    # Создание пользователя
    try:
        create_user(db, username, password, is_admin=is_admin)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "success": True,
            "message": "Пользователь создан успешно",
            "detail": f"Пользователь {username} создан",
            "username": username,
            "is_admin": is_admin
        }
    )


@router.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Вход в систему
    
    Args:
        form_data: Данные формы входа
        db: Сессия базы данных
    
    Returns:
        JSONResponse: JSON с токеном доступа и информацией о пользователе
    
    Raises:
        HTTPException: Если неверные учетные данные или аккаунт деактивирован
    """
    username = form_data.username.lower()
    
    # Проверка пользователя
    user = get_user_by_username(db, username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Проверка активности
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Аккаунт деактивирован"
        )
    
    # Проверка пароля
    if not verify_user_password(user, form_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Создание токена
    access_token_expires = timedelta(minutes=60 * 24)
    access_token = create_access_token(
        subject=user.username,
        expires_delta=access_token_expires
    )
    
    # Возвращаем is_admin для фронтенда
    response = JSONResponse(
        content={
            "success": True,
            "message": "Вход выполнен успешно",
            "is_admin": user.is_admin,
            "username": user.username
        }
    )
    
    # Установка cookie
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        path="/",
        httponly=True,
        secure=False,  # True для HTTPS в продакшене
        samesite="lax",
        max_age=60 * 60 * 24  # 24 часа
    )
    
    return response


@router.post("/logout")
def logout():
    """
    Выход из системы
    
    Returns:
        JSONResponse: JSON с результатом выхода
    """
    response = JSONResponse(
        content={
            "success": True,
            "message": "Выход выполнен"
        }
    )
    response.delete_cookie(key="access_token")
    return response


@router.get("/me")
def get_me(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Получить информацию о текущем пользователе
    
    Args:
        current_user: Текущий пользователь
        db: Сессия базы данных
    
    Returns:
        dict: Информация о пользователе
    
    Raises:
        HTTPException: Если пользователь не найден
    """
    user = get_user_by_username(db, current_user["username"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )
    
    return {
        "username": user.username,
        "is_admin": user.is_admin,
        "is_active": user.is_active
    }


# -----------------------------------------------------------------------------
# API для администраторов
# -----------------------------------------------------------------------------

@router.get("/users")
def get_all_users_endpoint(
    admin: dict = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Получить список всех пользователей (только для админов)
    
    Args:
        admin: Текущий пользователь-администратор
        db: Сессия базы данных
    
    Returns:
        dict: Список пользователей и их общее количество
    
    Raises:
        HTTPException: Если пользователь не администратор
    """
    users = get_all_users(db)
    users_list = [
        {
            "username": u.username,
            "is_admin": u.is_admin,
            "is_active": u.is_active
        }
        for u in users
    ]
    return {"users": users_list, "total": len(users_list)}


@router.get("/users/{username}")
def get_user(
    username: str,
    admin: dict = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Получить информацию о пользователе (только для админов)
    
    Args:
        username: Имя пользователя
        admin: Текущий пользователь-администратор
        db: Сессия базы данных
    
    Returns:
        dict: Информация о пользователе
    
    Raises:
        HTTPException: Если пользователь не найден или текущий пользователь не администратор
    """
    user = get_user_by_username(db, username.lower())
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )
    
    return {
        "username": user.username,
        "is_admin": user.is_admin,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if hasattr(user, 'created_at') else None
    }


class UserUpdate(BaseModel):
    """
    Модель для обновления пользователя
    """
    password: Optional[str] = None
    is_admin: Optional[bool] = None


@router.put("/users/{username}")
def update_user_endpoint(
    username: str,
    user_update: UserUpdate,
    admin: dict = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Обновить пользователя (только для админов)
    
    Args:
        username: Имя пользователя
        user_update: Данные для обновления
        admin: Текущий пользователь-администратор
        db: Сессия базы данных
    
    Returns:
        dict: Результат обновления
    
    Raises:
        HTTPException: Если пользователь не найден или валидация не пройдена
    """
    user = get_user_by_username(db, username.lower())
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )
    
    # Подготовка данных для обновления
    update_data = {}
    if user_update.password is not None:
        if len(user_update.password) < 6:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Пароль должен содержать минимум 6 символов"
            )
        update_data["password"] = user_update.password
    
    if user_update.is_admin is not None:
        update_data["is_admin"] = user_update.is_admin
    
    # Обновление пользователя
    update_user(db, user, **update_data)
    
    return {
        "success": True,
        "message": f"Пользователь {username} обновлён",
        "username": user.username,
        "is_admin": user.is_admin,
        "is_active": user.is_active
    }


@router.post("/users/{username}/toggle-status")
def toggle_user_status_endpoint(
    username: str,
    admin: dict = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Переключить статус активности пользователя (только для админов)
    
    Args:
        username: Имя пользователя
        admin: Текущий пользователь-администратор
        db: Сессия базы данных
    
    Returns:
        dict: Результат изменения статуса
    
    Raises:
        HTTPException: Если пользователь не найден или текущий пользователь не администратор
    """
    user = get_user_by_username(db, username.lower())
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )
    
    toggle_user_status(db, user)
    
    return {
        "success": True,
        "message": f"Статус пользователя {username} изменён",
        "is_active": user.is_active
    }


@router.delete("/users/{username}")
def delete_user(
    username: str,
    admin: dict = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Удалить пользователя (только для админов)
    
    Args:
        username: Имя пользователя
        admin: Текущий пользователь-администратор
        db: Сессия базы данных
    
    Returns:
        dict: Результат удаления
    
    Raises:
        HTTPException: Если пользователь не найден, попытка удалить самого себя или текущий пользователь не администратор
    """
    # Запрет на удаление самого себя
    if username.lower() == admin["username"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя удалить самого себя"
        )
    
    user = get_user_by_username(db, username.lower())
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )
    
    delete_user_service(db, user)
    
    return {
        "success": True,
        "message": f"Пользователь {username} удалён"
    }

"""
Роутер для работы с QR объектами
"""
from fastapi import APIRouter, Request, Form, UploadFile, File, HTTPException, Depends
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.qr_object_service import (
    create_qr_object,
    get_qr_object_by_id,
    get_qr_object_by_string,
    get_all_qr_objects,
    update_qr_object,
    delete_qr_object,
    qr_object_to_dict
)
from app.services.file_utils import save_file, delete_file
from app.services.auth import get_current_user, get_current_user_optional
from app.services.user_service import get_user_by_username

router = APIRouter(prefix="/qr", tags=["qr"])
templates = Jinja2Templates(directory="app/templates")


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
        raise HTTPException(status_code=403, detail="Только администраторы могут выполнять это действие")
    return current_user


@router.get("/objects", include_in_schema=False)
def list_qr_objects(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Список всех QR объектов (только для админов)
    
    Args:
        request: HTTP запрос
        db: Сессия базы данных
        current_user: Текущий пользователь
    
    Returns:
        HTMLResponse: HTML страница управления QR объектами
    
    Raises:
        HTTPException: Если пользователь не администратор или не авторизован
    """
    user = get_user_by_username(db, current_user.get("username"))
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут просматривать QR объекты")
    
    qr_objects = get_all_qr_objects(db)
    qr_objects_dict = [qr_object_to_dict(obj) for obj in qr_objects]
    
    user_info = {
        "username": user.username,
        "is_admin": user.is_admin
    }
    
    return templates.TemplateResponse(
        "qr_objects_manage.html",
        {
            "request": request,
            "qr_objects": qr_objects_dict,
            "current_user": user_info
        }
    )


@router.get("/objects/create", include_in_schema=False)
def create_qr_object_form(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Форма создания QR объекта
    
    Args:
        request: HTTP запрос
        db: Сессия базы данных
        current_user: Текущий пользователь
    
    Returns:
        HTMLResponse: HTML страница формы создания
    
    Raises:
        HTTPException: Если пользователь не администратор
    """
    user = get_user_by_username(db, current_user.get("username"))
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут создавать QR объекты")
    
    return templates.TemplateResponse(
        "create_qr_object.html",
        {
            "request": request,
            "title": "Создать QR объект"
        }
    )


@router.post("/objects/create", include_in_schema=False)
async def create_qr_object_route(
    request: Request,
    db: Session = Depends(get_db),
    name: str = Form(...),
    description: str = Form(None),
    photo: UploadFile | None = File(None),
    current_user: dict = Depends(get_current_user)
):
    """
    Создание нового QR объекта
    
    Args:
        request: HTTP запрос
        db: Сессия базы данных
        name: Название объекта
        description: Описание объекта (HTML)
        photo: Фото объекта
        current_user: Текущий пользователь
    
    Returns:
        RedirectResponse: Редирект на список объектов или JSON с ошибкой
    
    Raises:
        HTTPException: Если пользователь не администратор или ошибка валидации
    """
    user = get_user_by_username(db, current_user.get("username"))
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут создавать QR объекты")
    
    # Валидация
    if not name or len(name.strip()) == 0:
        return JSONResponse(
            status_code=400,
            content={"detail": "Название не может быть пустым"}
        )
    
    photo_path = None
    try:
        # Сохранение фото
        if photo and photo.filename:
            photo_path = save_file(photo, file_type="image")
        
        # Получаем базовый URL из запроса
        base_url = str(request.base_url).rstrip('/')
        
        # Создание QR объекта (QR код генерируется автоматически)
        qr_object = create_qr_object(
            name=name.strip(),
            description=description if description else None,  # HTML контент сохраняем как есть
            photo=photo_path,
            created_by=user.username,
            db=db,
            base_url=base_url
        )
        
        return RedirectResponse(url="/qr/objects", status_code=303)
        
    except Exception as e:
        # Удаляем загруженный файл в случае ошибки
        if photo_path:
            delete_file(photo_path)
        
        return JSONResponse(
            status_code=500,
            content={"detail": f"Ошибка при создании QR объекта: {str(e)}"}
        )


@router.post("/objects/{object_id}/delete", include_in_schema=False)
async def delete_qr_object_route(
    object_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Удаление QR объекта
    
    Args:
        object_id: ID объекта
        db: Сессия базы данных
        current_user: Текущий пользователь
    
    Returns:
        RedirectResponse: Редирект на список объектов
    
    Raises:
        HTTPException: Если пользователь не администратор или объект не найден
    """
    user = get_user_by_username(db, current_user.get("username"))
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут удалять QR объекты")
    
    qr_object = get_qr_object_by_id(object_id, db)
    if not qr_object:
        raise HTTPException(status_code=404, detail="QR объект не найден")
    
    delete_qr_object(object_id, db)
    
    return RedirectResponse(url="/qr/objects", status_code=303)


@router.get("/api/search")
def search_qr_by_string(
    qr_string: str,
    db: Session = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    API endpoint для поиска QR объекта по строке из QR кода

    Args:
        qr_string: Строка, полученная при сканировании QR кода
        db: Сессия базы данных
        current_user: Текущий пользователь (опционально)

    Returns:
        JSONResponse: Данные найденного объекта

    Raises:
        HTTPException: Если объект не найден
    """
    qr_object = get_qr_object_by_string(qr_string, db)
    if not qr_object:
        raise HTTPException(status_code=404, detail="QR объект не найден")

    object_dict = qr_object_to_dict(qr_object)

    return JSONResponse(content={
        "success": True,
        "data": object_dict
    })


@router.get("/view/{object_id}", include_in_schema=False)
def view_qr_object(
    object_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    Просмотр QR объекта (публичная страница, доступна без авторизации)

    Args:
        object_id: ID объекта
        request: HTTP запрос
        db: Сессия базы данных
        current_user: Текущий пользователь (опционально)

    Returns:
        HTMLResponse: HTML страница с информацией об объекте

    Raises:
        HTTPException: Если объект не найден
    """
    qr_object = get_qr_object_by_id(object_id, db)
    if not qr_object:
        raise HTTPException(status_code=404, detail="QR объект не найден")

    object_dict = qr_object_to_dict(qr_object)

    return templates.TemplateResponse(
        "qr_object_view.html",
        {
            "request": request,
            "qr_object": object_dict,
            "current_user": current_user
        }
    )


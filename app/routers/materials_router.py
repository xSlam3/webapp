"""
Роутер для работы с материалами базы знаний
"""
from fastapi import APIRouter, Request, Form, UploadFile, File, HTTPException, Depends
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.material_models import Material
from app.services.knowledge_base_utils import (
    create_material,
    read_materials,
    read_material_by_id,
    update_material,
    delete_material
)
from app.services.file_utils import save_file, delete_file
from app.services.auth import get_current_user, get_current_user_optional
from app.services.user_service import get_user_by_username
from app.services.material_service import search_materials as db_search_materials

router = APIRouter(prefix="/knowledge_base", tags=["knowledge-base"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", include_in_schema=False)
def list_materials(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Список всех материалов
    
    Args:
        request: HTTP запрос
        db: Сессия базы данных
        current_user: Текущий пользователь
    
    Returns:
        HTMLResponse: HTML страница со списком материалов
    
    Raises:
        HTTPException: Если пользователь не авторизован
    """
    materials = read_materials(db)
    
    # Получаем полную информацию о пользователе для шаблона
    user = get_user_by_username(db, current_user.get("username"))
    if not user or not user.is_active:
        return RedirectResponse(url="/auth/", status_code=303)
    
    user_info = {
        "username": user.username,
        "is_admin": user.is_admin
    }
    
    return templates.TemplateResponse(
        "materials_list.html", 
        {
            "request": request, 
            "materials": materials,
            "current_user": user_info
        }
    )


@router.get("/create", include_in_schema=False)
def create_form(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Форма создания материала
    
    Args:
        request: HTTP запрос
        db: Сессия базы данных
        current_user: Текущий пользователь
    
    Returns:
        HTMLResponse: HTML страница формы создания
    
    Raises:
        HTTPException: Если пользователь не администратор или не авторизован
    """
    user = get_user_by_username(db, current_user.get("username"))
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут создавать материалы")
    
    user_info = {
        "username": user.username,
        "is_admin": user.is_admin
    }
    
    return templates.TemplateResponse(
        "create_material.html", 
        {
            "request": request,
            "current_user": user_info
        }
    )


@router.get("/api/search", include_in_schema=False)
def search_api(
    q: str = "",
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    API для поиска материалов
    
    Args:
        q: Поисковый запрос
        db: Сессия базы данных
        current_user: Текущий пользователь
    
    Returns:
        JSONResponse: JSON с результатами поиска
    
    Raises:
        HTTPException: Если пользователь не авторизован
    """
    if not q:
        materials = read_materials(db)
        return JSONResponse(content={"materials": materials})
    
    # Используем поиск через БД
    db_materials = db_search_materials(db, q)
    materials = [
        {
            "id": m.id,
            "title": m.title,
            "text": m.text,
            "photo": m.photo,
            "video": m.video,
            "created_by": m.created_by,
            "created_at": m.created_at.isoformat() if m.created_at else None,
            "updated_at": m.updated_at.isoformat() if m.updated_at else None
        }
        for m in db_materials
    ]
    
    return JSONResponse(content={"materials": materials})


@router.post("/create", include_in_schema=False)
async def submit_create(
    request: Request,
    db: Session = Depends(get_db),
    title: str = Form(...),
    text: str = Form(None),
    photo: UploadFile | None = File(None),
    video: UploadFile | None = File(None),
    current_user: dict = Depends(get_current_user)
):
    """
    Создание нового материала
    
    Args:
        request: HTTP запрос
        db: Сессия базы данных
        title: Заголовок материала
        text: Текст материала
        photo: Фото файл (опционально)
        video: Видео файл (опционально)
        current_user: Текущий пользователь
    
    Returns:
        RedirectResponse: Редирект на список материалов или JSON с ошибкой
    
    Raises:
        HTTPException: Если пользователь не администратор или ошибка валидации
    """
    user = get_user_by_username(db, current_user.get("username"))
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут создавать материалы")
    
    # Валидация заголовка
    if not title or len(title.strip()) == 0:
        return JSONResponse(
            status_code=400,
            content={"detail": "Заголовок не может быть пустым"}
        )
    
    photo_path = None
    video_path = None
    
    try:
        # Сохранение файлов
        if photo and photo.filename:
            photo_path = save_file(photo, file_type="image")
        
        if video and video.filename:
            video_path = save_file(video, file_type="video")
        
        # Создание материала
        # Для HTML контента не используем strip(), чтобы сохранить форматирование
        material = Material(
            id=0,  # id назначается в сервисе
            title=title.strip(),
            text=text if text else None,  # HTML контент сохраняем как есть
            photo=photo_path,
            video=video_path
        )
        create_material(material, db, created_by=user.username)
        
        return RedirectResponse(url="/knowledge_base/", status_code=303)
        
    except HTTPException as e:
        # Удаляем загруженные файлы в случае ошибки
        if photo_path:
            delete_file(photo_path)
        if video_path:
            delete_file(video_path)
        
        return JSONResponse(
            status_code=e.status_code,
            content={"detail": e.detail}
        )
    except Exception as e:
        # Удаляем загруженные файлы в случае ошибки
        if photo_path:
            delete_file(photo_path)
        if video_path:
            delete_file(video_path)
        
        return JSONResponse(
            status_code=500,
            content={"detail": f"Ошибка при создании материала: {str(e)}"}
        )


@router.get("/{material_id}", include_in_schema=False)
def material_detail(
    request: Request, 
    material_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Детальная страница материала
    
    Args:
        request: HTTP запрос
        material_id: ID материала
        db: Сессия базы данных
        current_user: Текущий пользователь
    
    Returns:
        HTMLResponse: HTML страница деталей материала
    
    Raises:
        HTTPException: Если материал не найден или пользователь не авторизован
    """
    material = read_material_by_id(material_id, db)
    if not material:
        raise HTTPException(status_code=404, detail="Материал не найден")
    
    # Получаем полную информацию о пользователе для шаблона
    user = get_user_by_username(db, current_user.get("username"))
    if not user or not user.is_active:
        return RedirectResponse(url="/auth/", status_code=303)
    
    user_info = {
        "username": user.username,
        "is_admin": user.is_admin
    }
    
    return templates.TemplateResponse(
        "material_detail.html", 
        {
            "request": request, 
            "material": material,
            "current_user": user_info
        }
    )


@router.get("/{material_id}/edit", include_in_schema=False)
def edit_form(
    request: Request, 
    material_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Форма редактирования материала
    
    Args:
        request: HTTP запрос
        material_id: ID материала
        db: Сессия базы данных
        current_user: Текущий пользователь
    
    Returns:
        HTMLResponse: HTML страница формы редактирования
    
    Raises:
        HTTPException: Если пользователь не администратор или материал не найден
    """
    user = get_user_by_username(db, current_user.get("username"))
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут редактировать материалы")
    
    material = read_material_by_id(material_id, db)
    if not material:
        raise HTTPException(status_code=404, detail="Материал не найден")
    
    user_info = {
        "username": user.username,
        "is_admin": user.is_admin
    }
    
    return templates.TemplateResponse(
        "edit_material.html", 
        {
            "request": request, 
            "material": material,
            "current_user": user_info
        }
    )


@router.post("/{material_id}/edit", include_in_schema=False)
async def submit_edit(
    request: Request,
    material_id: int,
    db: Session = Depends(get_db),
    title: str = Form(...),
    text: str = Form(None),
    photo: UploadFile | None = File(None),
    video: UploadFile | None = File(None),
    remove_photo: str = Form(None),
    remove_video: str = Form(None),
    current_user: dict = Depends(get_current_user)
):
    """
    Редактирование существующего материала
    
    Args:
        request: HTTP запрос
        material_id: ID материала
        db: Сессия базы данных
        title: Заголовок материала
        text: Текст материала
        photo: Новое фото файл (опционально)
        video: Новое видео файл (опционально)
        remove_photo: Флаг удаления фото
        remove_video: Флаг удаления видео
        current_user: Текущий пользователь
    
    Returns:
        RedirectResponse: Редирект на детальную страницу материала
    
    Raises:
        HTTPException: Если пользователь не администратор или материал не найден
    """
    user = get_user_by_username(db, current_user.get("username"))
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут редактировать материалы")
    
    material = read_material_by_id(material_id, db)
    if not material:
        raise HTTPException(status_code=404, detail="Материал не найден")
    
    # Валидация заголовка
    if not title or len(title.strip()) == 0:
        raise HTTPException(status_code=400, detail="Заголовок не может быть пустым")
    
    updated_data = {
        "title": title.strip(), 
        "text": text if text else None  # HTML контент сохраняем как есть
    }
    
    # Удаление фото
    if remove_photo == "true" and material.get("photo"):
        delete_file(material["photo"])
        updated_data["photo"] = None
    
    # Удаление видео
    if remove_video == "true" and material.get("video"):
        delete_file(material["video"])
        updated_data["video"] = None
    
    # Загрузка нового фото
    if photo and photo.filename:
        new_photo = save_file(photo, file_type="image")
        if new_photo:
            # Удаляем старое фото
            if material.get("photo"):
                delete_file(material["photo"])
            updated_data["photo"] = new_photo
    
    # Загрузка нового видео
    if video and video.filename:
        new_video = save_file(video, file_type="video")
        if new_video:
            # Удаляем старое видео
            if material.get("video"):
                delete_file(material["video"])
            updated_data["video"] = new_video
    
    update_material(material_id, updated_data, db)
    return RedirectResponse(url=f"/knowledge_base/{material_id}", status_code=303)


@router.post("/{material_id}/delete", include_in_schema=False)
async def delete_material_route(
    material_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Удаление материала
    
    Args:
        material_id: ID материала
        db: Сессия базы данных
        current_user: Текущий пользователь
    
    Returns:
        RedirectResponse: Редирект на список материалов
    
    Raises:
        HTTPException: Если пользователь не администратор или материал не найден
    """
    user = get_user_by_username(db, current_user.get("username"))
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут удалять материалы")
    
    material = read_material_by_id(material_id, db)
    if not material:
        raise HTTPException(status_code=404, detail="Материал не найден")
    
    # Удаляем файлы
    if material.get("photo"):
        delete_file(material["photo"])
    
    if material.get("video"):
        delete_file(material["video"])
    
    delete_material(material_id, db)
    return RedirectResponse(url="/knowledge_base/", status_code=303)

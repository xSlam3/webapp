"""
Роутер для работы с AR тегами
"""
from fastapi import APIRouter, Request, Form, UploadFile, File, HTTPException, Depends
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.ar_tag_service import (
    create_ar_tag,
    get_ar_tag_by_id,
    get_all_ar_tags,
    update_ar_tag,
    delete_ar_tag,
    ar_tag_to_dict,
    get_ar_tag_by_material_id
)
from app.services.file_utils import save_file, delete_file
from app.services.auth import get_current_user, get_current_user_optional
from app.services.user_service import get_user_by_username
from app.services.knowledge_base_utils import read_materials
from app.models.material_db_models import Material

router = APIRouter(prefix="/ar", tags=["ar"])
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


@router.get("/tags", include_in_schema=False)
def list_ar_tags(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Список всех AR тегов (только для админов)
    
    Args:
        request: HTTP запрос
        db: Сессия базы данных
        current_user: Текущий пользователь
    
    Returns:
        HTMLResponse: HTML страница управления AR тегами
    
    Raises:
        HTTPException: Если пользователь не администратор или не авторизован
    """
    user = get_user_by_username(db, current_user.get("username"))
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут просматривать AR теги")
    
    ar_tags = get_all_ar_tags(db)
    ar_tags_dict = [ar_tag_to_dict(tag, db, include_material=True) for tag in ar_tags]
    
    # Получаем все материалы для выпадающего списка
    materials = read_materials(db)
    
    user_info = {
        "username": user.username,
        "is_admin": user.is_admin
    }
    
    return templates.TemplateResponse(
        "ar_tags_manage.html",
        {
            "request": request,
            "ar_tags": ar_tags_dict,
            "materials": materials,
            "current_user": user_info
        }
    )


@router.get("/tags/create", include_in_schema=False)
def create_ar_tag_form(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Форма создания AR тега
    
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
        raise HTTPException(status_code=403, detail="Только администраторы могут создавать AR теги")
    
    materials = read_materials(db)
    
    return templates.TemplateResponse(
        "create_ar_tag.html",
        {
            "request": request,
            "title": "Создать AR тег",
            "materials": materials
        }
    )


@router.post("/tags/create", include_in_schema=False)
async def create_ar_tag_route(
    request: Request,
    db: Session = Depends(get_db),
    name: str = Form(...),
    description: str = Form(None),
    tag_image: UploadFile = File(...),
    material_id: int = Form(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Создание нового AR тега
    
    Args:
        request: HTTP запрос
        db: Сессия базы данных
        name: Название тега
        description: Описание тега
        tag_image: Изображение тега
        material_id: ID связанного материала
        current_user: Текущий пользователь
    
    Returns:
        RedirectResponse: Редирект на список тегов или JSON с ошибкой
    
    Raises:
        HTTPException: Если пользователь не администратор или ошибка валидации
    """
    user = get_user_by_username(db, current_user.get("username"))
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут создавать AR теги")
    
    # Валидация
    if not name or len(name.strip()) == 0:
        return JSONResponse(
            status_code=400,
            content={"detail": "Название не может быть пустым"}
        )
    
    # Проверка существования материала
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        return JSONResponse(
            status_code=400,
            content={"detail": "Материал не найден"}
        )
    
    tag_image_path = None
    try:
        # Сохранение изображения тега
        if tag_image and tag_image.filename:
            tag_image_path = save_file(tag_image, file_type="image")
        
        # Создание AR тега
        # Для HTML контента не используем strip(), чтобы сохранить форматирование
        ar_tag = create_ar_tag(
            name=name.strip(),
            description=description if description else None,  # HTML контент сохраняем как есть
            tag_image=tag_image_path,
            material_id=material_id,
            created_by=user.username,
            db=db
        )
        
        return RedirectResponse(url="/ar/tags", status_code=303)
        
    except Exception as e:
        # Удаляем загруженный файл в случае ошибки
        if tag_image_path:
            delete_file(tag_image_path)
        
        return JSONResponse(
            status_code=500,
            content={"detail": f"Ошибка при создании AR тега: {str(e)}"}
        )


@router.post("/tags/{tag_id}/delete", include_in_schema=False)
async def delete_ar_tag_route(
    tag_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Удаление AR тега
    
    Args:
        tag_id: ID тега
        db: Сессия базы данных
        current_user: Текущий пользователь
    
    Returns:
        RedirectResponse: Редирект на список тегов
    
    Raises:
        HTTPException: Если пользователь не администратор или тег не найден
    """
    user = get_user_by_username(db, current_user.get("username"))
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут удалять AR теги")
    
    ar_tag = get_ar_tag_by_id(tag_id, db)
    if not ar_tag:
        raise HTTPException(status_code=404, detail="AR тег не найден")
    
    # Удаляем файл изображения
    if ar_tag.tag_image:
        delete_file(ar_tag.tag_image)
    
    delete_ar_tag(tag_id, db)
    return RedirectResponse(url="/ar/tags", status_code=303)


@router.get("/scanner", include_in_schema=False)
def ar_scanner_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Страница AR сканера для пользователей
    
    Args:
        request: HTTP запрос
        db: Сессия базы данных
        current_user: Текущий пользователь
    
    Returns:
        HTMLResponse: HTML страница AR сканера
    
    Raises:
        HTTPException: Если пользователь не авторизован
    """
    user = get_user_by_username(db, current_user.get("username"))
    if not user or not user.is_active:
        return RedirectResponse(url="/auth/", status_code=303)
    
    user_info = {
        "username": user.username,
        "is_admin": user.is_admin
    }
    
    return templates.TemplateResponse(
        "ar_scanner.html",
        {
            "request": request,
            "current_user": user_info
        }
    )


@router.get("/api/tag/{tag_id}/material", include_in_schema=False)
def get_material_by_tag(
    tag_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    API для получения материала по ID тега
    
    Args:
        tag_id: ID тега
        db: Сессия базы данных
        current_user: Текущий пользователь
    
    Returns:
        JSONResponse: JSON с данными материала и тега
    
    Raises:
        HTTPException: Если тег или материал не найдены, или пользователь не авторизован
    """
    ar_tag = get_ar_tag_by_id(tag_id, db)
    if not ar_tag:
        raise HTTPException(status_code=404, detail="AR тег не найден")
    
    material = db.query(Material).filter(Material.id == ar_tag.material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Материал не найден")
    
    return JSONResponse(content={
        "material": {
            "id": material.id,
            "title": material.title,
            "text": material.text,
            "photo": material.photo,
            "video": material.video,
            "created_at": material.created_at.isoformat() if material.created_at else None
        },
        "tag": {
            "id": ar_tag.id,
            "name": ar_tag.name,
            "description": ar_tag.description
        }
    })


@router.get("/api/tags", include_in_schema=False)
def get_all_tags_api(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    API для получения всех AR тегов (для AR.js)
    
    Args:
        db: Сессия базы данных
        current_user: Текущий пользователь
    
    Returns:
        JSONResponse: JSON со списком всех AR тегов
    
    Raises:
        HTTPException: Если пользователь не авторизован
    """
    ar_tags = get_all_ar_tags(db)
    tags_data = []
    
    for tag in ar_tags:
        material = db.query(Material).filter(Material.id == tag.material_id).first()
        tags_data.append({
            "id": tag.id,
            "name": tag.name,
            "tag_image_url": f"/static/{tag.tag_image}",
            "material_id": tag.material_id,
            "material_title": material.title if material else "Неизвестный материал"
        })
    
    return JSONResponse(content={"tags": tags_data})


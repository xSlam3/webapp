"""
Unified router for AR and QR scanning functionality
"""
from fastapi import APIRouter, Request, Form, UploadFile, File, HTTPException, Depends
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.ar_tag_service import (
    create_ar_tag,
    get_ar_tag_by_id,
    get_all_ar_tags,
    delete_ar_tag,
    ar_tag_to_dict
)
from app.services.qr_object_service import (
    create_qr_object,
    get_qr_object_by_id,
    get_qr_object_by_string,
    get_all_qr_objects,
    delete_qr_object,
    qr_object_to_dict
)
from app.services.file_utils import save_file, delete_file
from app.services.auth import get_current_user, get_current_user_optional
from app.services.user_service import get_user_by_username
from app.models.material_db_models import Material

router = APIRouter(prefix="/scanner", tags=["scanner"])
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


# ============= Management Routes =============

@router.get("/manage", include_in_schema=False)
def list_all_objects(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Список всех интерактивных объектов (AR теги и QR объекты)

    Args:
        request: HTTP запрос
        db: Сессия базы данных
        current_user: Текущий пользователь

    Returns:
        HTMLResponse: HTML страница управления объектами
    """
    user = get_user_by_username(db, current_user.get("username"))
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут просматривать объекты")

    # Получаем все AR теги
    ar_tags = get_all_ar_tags(db)
    ar_objects = []
    for tag in ar_tags:
        obj_dict = ar_tag_to_dict(tag, db, include_material=False)
        obj_dict['type'] = 'ar'
        ar_objects.append(obj_dict)

    # Получаем все QR объекты
    qr_objects = get_all_qr_objects(db)
    qr_objects_list = []
    for obj in qr_objects:
        obj_dict = qr_object_to_dict(obj)
        obj_dict['type'] = 'qr'
        qr_objects_list.append(obj_dict)

    # Объединяем и сортируем по дате создания
    all_objects = ar_objects + qr_objects_list
    all_objects.sort(key=lambda x: x.get('created_at', ''), reverse=True)

    user_info = {
        "username": user.username,
        "is_admin": user.is_admin
    }

    return templates.TemplateResponse(
        "scanner_manage.html",
        {
            "request": request,
            "objects": all_objects,
            "current_user": user_info
        }
    )


@router.get("/create", include_in_schema=False)
def create_object_form(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Форма создания интерактивного объекта (AR или QR)

    Args:
        request: HTTP запрос
        db: Сессия базы данных
        current_user: Текущий пользователь

    Returns:
        HTMLResponse: HTML страница формы создания
    """
    user = get_user_by_username(db, current_user.get("username"))
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут создавать объекты")

    return templates.TemplateResponse(
        "scanner_create.html",
        {
            "request": request,
            "title": "Создать интерактивный объект"
        }
    )


@router.post("/create", include_in_schema=False)
async def create_object_route(
    request: Request,
    db: Session = Depends(get_db),
    object_type: str = Form(...),
    name: str = Form(...),
    description: str = Form(None),
    image: UploadFile | None = File(None),
    photo: UploadFile | None = File(None),
    current_user: dict = Depends(get_current_user)
):
    """
    Создание нового интерактивного объекта (AR или QR)

    Args:
        request: HTTP запрос
        db: Сессия базы данных
        object_type: Тип объекта ('ar' или 'qr')
        name: Название объекта
        description: Описание объекта
        image: Изображение для AR тега
        photo: Фото для QR объекта
        current_user: Текущий пользователь

    Returns:
        RedirectResponse: Редирект на список объектов или JSON с ошибкой
    """
    user = get_user_by_username(db, current_user.get("username"))
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут создавать объекты")

    # Валидация
    if not name or len(name.strip()) == 0:
        return JSONResponse(
            status_code=400,
            content={"detail": "Название не может быть пустым"}
        )

    if object_type not in ['ar', 'qr']:
        return JSONResponse(
            status_code=400,
            content={"detail": "Неверный тип объекта"}
        )

    try:
        if object_type == 'ar':
            # Создание AR тега
            if not image or not image.filename:
                return JSONResponse(
                    status_code=400,
                    content={"detail": "Изображение обязательно для AR тега"}
                )

            # Сохранение изображения тега
            tag_image_path = save_file(image, file_type="image")

            # Создание AR тега без привязки к материалу
            ar_tag = create_ar_tag(
                name=name.strip(),
                description=description if description else None,
                tag_image=tag_image_path,
                material_id=None,  # Больше не требуется
                created_by=user.username,
                db=db
            )

        else:  # object_type == 'qr'
            # Создание QR объекта
            photo_path = None
            if photo and photo.filename:
                photo_path = save_file(photo, file_type="image")

            # Получаем базовый URL из запроса
            base_url = str(request.base_url).rstrip('/')

            # Создание QR объекта
            qr_object = create_qr_object(
                name=name.strip(),
                description=description if description else None,
                photo=photo_path,
                created_by=user.username,
                db=db,
                base_url=base_url
            )

        return RedirectResponse(url="/scanner/manage", status_code=303)

    except Exception as e:
        # Удаляем загруженные файлы в случае ошибки
        if object_type == 'ar' and 'tag_image_path' in locals():
            delete_file(tag_image_path)
        elif object_type == 'qr' and 'photo_path' in locals() and photo_path:
            delete_file(photo_path)

        return JSONResponse(
            status_code=500,
            content={"detail": f"Ошибка при создании объекта: {str(e)}"}
        )


@router.post("/delete/{object_type}/{object_id}", include_in_schema=False)
async def delete_object_route(
    object_type: str,
    object_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Удаление интерактивного объекта

    Args:
        object_type: Тип объекта ('ar' или 'qr')
        object_id: ID объекта
        db: Сессия базы данных
        current_user: Текущий пользователь

    Returns:
        RedirectResponse: Редирект на список объектов
    """
    user = get_user_by_username(db, current_user.get("username"))
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут удалять объекты")

    if object_type == 'ar':
        ar_tag = get_ar_tag_by_id(object_id, db)
        if not ar_tag:
            raise HTTPException(status_code=404, detail="AR тег не найден")

        # Удаляем файл изображения
        if ar_tag.tag_image:
            delete_file(ar_tag.tag_image)

        delete_ar_tag(object_id, db)
    elif object_type == 'qr':
        qr_object = get_qr_object_by_id(object_id, db)
        if not qr_object:
            raise HTTPException(status_code=404, detail="QR объект не найден")

        delete_qr_object(object_id, db)
    else:
        raise HTTPException(status_code=400, detail="Неверный тип объекта")

    return RedirectResponse(url="/scanner/manage", status_code=303)


# ============= Scanner Page =============

@router.get("/", include_in_schema=False)
def scanner_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Страница сканера для пользователей (AR и QR)

    Args:
        request: HTTP запрос
        db: Сессия базы данных
        current_user: Текущий пользователь

    Returns:
        HTMLResponse: HTML страница сканера
    """
    user = get_user_by_username(db, current_user.get("username"))
    if not user or not user.is_active:
        return RedirectResponse(url="/auth/", status_code=303)

    user_info = {
        "username": user.username,
        "is_admin": user.is_admin
    }

    return templates.TemplateResponse(
        "scanner.html",
        {
            "request": request,
            "current_user": user_info
        }
    )


# ============= API Routes =============

@router.get("/api/tags", include_in_schema=False)
def get_all_tags_api(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    API для получения всех AR тегов (для распознавания)

    Args:
        db: Сессия базы данных
        current_user: Текущий пользователь

    Returns:
        JSONResponse: JSON со списком всех AR тегов
    """
    ar_tags = get_all_ar_tags(db)
    tags_data = []

    for tag in ar_tags:
        tags_data.append({
            "id": tag.id,
            "name": tag.name,
            "tag_image_url": f"/static/{tag.tag_image}",
            "description": tag.description
        })

    return JSONResponse(content={"tags": tags_data})


@router.post("/api/match-image", include_in_schema=False)
async def match_image_with_orb(
    request: Request,
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    API для распознавания изображения через ORB

    Args:
        request: HTTP запрос
        image: Изображение с камеры для распознавания
        db: Сессия базы данных
        current_user: Текущий пользователь

    Returns:
        JSONResponse: JSON с результатом распознавания
    """
    from app.services.orb_service import match_orb_features

    try:
        # Читаем изображение
        image_data = await image.read()

        if not image_data:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "Пустое изображение"}
            )

        # Получаем все AR теги с ORB признаками
        ar_tags = get_all_ar_tags(db)

        best_match = None
        best_confidence = 0.0
        best_match_count = 0

        # Проверяем изображение против каждого тега
        for tag in ar_tags:
            # Пропускаем теги без ORB признаков
            if not tag.orb_keypoints or not tag.orb_descriptors:
                continue

            # Сопоставляем признаки
            matched, confidence, match_count = match_orb_features(
                query_image_data=image_data,
                target_keypoints_json=tag.orb_keypoints,
                target_descriptors_bytes=tag.orb_descriptors,
                min_match_count=10,
                ratio_threshold=0.75
            )

            print(f"Тег '{tag.name}' (ID: {tag.id}): matched={matched}, confidence={confidence:.2f}%, matches={match_count}")

            # Сохраняем лучший результат
            if matched and confidence > best_confidence:
                best_match = tag
                best_confidence = confidence
                best_match_count = match_count

        # Если найдено совпадение
        if best_match:
            result = {
                "success": True,
                "matched": True,
                "tag_id": best_match.id,
                "tag_name": best_match.name,
                "confidence": round(best_confidence, 2),
                "match_count": best_match_count,
                "content": {
                    "name": best_match.name,
                    "description": best_match.description
                }
            }

            print(f"Найдено совпадение: {best_match.name} с уверенностью {best_confidence:.2f}%")
            return JSONResponse(content=result)

        # Совпадение не найдено
        return JSONResponse(content={
            "success": True,
            "matched": False,
            "message": "Изображение не распознано"
        })

    except Exception as e:
        print(f"Ошибка распознавания изображения: {e}")
        import traceback
        traceback.print_exc()

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Ошибка обработки: {str(e)}"
            }
        )


@router.get("/api/qr/search")
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
    """
    qr_object = get_qr_object_by_string(qr_string, db)
    if not qr_object:
        raise HTTPException(status_code=404, detail="QR объект не найден")

    object_dict = qr_object_to_dict(qr_object)

    return JSONResponse(content={
        "success": True,
        "data": object_dict
    })


@router.get("/view/qr/{object_id}", include_in_schema=False)
def view_qr_object(
    object_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    Просмотр QR объекта (публичная страница)

    Args:
        object_id: ID объекта
        request: HTTP запрос
        db: Сессия базы данных
        current_user: Текущий пользователь (опционально)

    Returns:
        HTMLResponse: HTML страница с информацией об объекте
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

"""
Роутер для работы с интерактивными объектами (AR и QR)
"""
from fastapi import APIRouter, Request, Form, UploadFile, File, HTTPException, Depends
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.interactive_object_db_models import ObjectType
from app.services.interactive_object_service import (
    create_interactive_object,
    get_interactive_object_by_id,
    get_interactive_object_by_qr_string,
    get_all_interactive_objects,
    get_ar_objects_for_recognition,
    update_interactive_object,
    delete_interactive_object,
    interactive_object_to_dict
)
from app.services.file_utils import save_file, delete_file
from app.services.auth import get_current_user, get_current_user_optional
from app.services.user_service import get_user_by_username

router = APIRouter(prefix="/objects", tags=["interactive_objects"])
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


@router.get("/manage", include_in_schema=False)
def list_interactive_objects(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Список всех интерактивных объектов (только для админов)

    Args:
        request: HTTP запрос
        db: Сессия базы данных
        current_user: Текущий пользователь

    Returns:
        HTMLResponse: HTML страница управления объектами

    Raises:
        HTTPException: Если пользователь не администратор или не авторизован
    """
    user = get_user_by_username(db, current_user.get("username"))
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут просматривать объекты")

    objects = get_all_interactive_objects(db)
    objects_dict = [interactive_object_to_dict(obj) for obj in objects]

    user_info = {
        "username": user.username,
        "is_admin": user.is_admin
    }

    return templates.TemplateResponse(
        "interactive_objects_manage.html",
        {
            "request": request,
            "objects": objects_dict,
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
    Форма создания интерактивного объекта

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
        raise HTTPException(status_code=403, detail="Только администраторы могут создавать объекты")

    return templates.TemplateResponse(
        "create_interactive_object.html",
        {
            "request": request,
            "title": "Создать интерактивный объект"
        }
    )


@router.post("/create", include_in_schema=False)
async def create_object_route(
    request: Request,
    db: Session = Depends(get_db),
    name: str = Form(...),
    description: str = Form(None),
    object_type: str = Form(...),
    photo: UploadFile | None = File(None),
    recognition_image: UploadFile | None = File(None),
    current_user: dict = Depends(get_current_user)
):
    """
    Создание нового интерактивного объекта

    Args:
        request: HTTP запрос
        db: Сессия базы данных
        name: Название объекта
        description: Описание объекта (HTML) - статья для отображения
        object_type: Тип объекта ('ar' или 'qr')
        photo: Фото объекта для отображения
        recognition_image: Изображение для распознавания (только для AR)
        current_user: Текущий пользователь

    Returns:
        RedirectResponse: Редирект на список объектов или JSON с ошибкой

    Raises:
        HTTPException: Если пользователь не администратор или ошибка валидации
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

    # Проверка типа объекта
    try:
        obj_type = ObjectType(object_type)
    except ValueError:
        return JSONResponse(
            status_code=400,
            content={"detail": "Неверный тип объекта. Доступны: 'ar', 'qr'"}
        )

    # Проверка для AR объектов - требуется изображение для распознавания
    if obj_type == ObjectType.AR and (not recognition_image or not recognition_image.filename):
        return JSONResponse(
            status_code=400,
            content={"detail": "AR объект требует изображение для распознавания"}
        )

    photo_path = None
    recognition_image_path = None

    try:
        # Сохранение фото для отображения
        if photo and photo.filename:
            photo_path = save_file(photo, file_type="image")

        # Сохранение изображения для распознавания (только для AR)
        if recognition_image and recognition_image.filename:
            recognition_image_path = save_file(recognition_image, file_type="image")

        # Создание объекта
        obj = create_interactive_object(
            name=name.strip(),
            description=description if description else None,
            object_type=obj_type,
            photo=photo_path,
            recognition_image=recognition_image_path,
            created_by=user.username,
            db=db
        )

        return RedirectResponse(url="/objects/manage", status_code=303)

    except Exception as e:
        # Удаляем загруженные файлы в случае ошибки
        if photo_path:
            delete_file(photo_path)
        if recognition_image_path:
            delete_file(recognition_image_path)

        return JSONResponse(
            status_code=500,
            content={"detail": f"Ошибка при создании объекта: {str(e)}"}
        )


@router.get("/{object_id}/edit", include_in_schema=False)
def edit_object_form(
    object_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Форма редактирования интерактивного объекта

    Args:
        object_id: ID объекта
        request: HTTP запрос
        db: Сессия базы данных
        current_user: Текущий пользователь

    Returns:
        HTMLResponse: HTML страница формы редактирования

    Raises:
        HTTPException: Если пользователь не администратор или объект не найден
    """
    user = get_user_by_username(db, current_user.get("username"))
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут редактировать объекты")

    obj = get_interactive_object_by_id(object_id, db)
    if not obj:
        raise HTTPException(status_code=404, detail="Объект не найден")

    object_dict = interactive_object_to_dict(obj)

    return templates.TemplateResponse(
        "edit_interactive_object.html",
        {
            "request": request,
            "title": "Редактировать интерактивный объект",
            "object": object_dict
        }
    )


@router.post("/{object_id}/edit", include_in_schema=False)
async def edit_object_route(
    object_id: int,
    request: Request,
    db: Session = Depends(get_db),
    name: str = Form(...),
    description: str = Form(None),
    photo: UploadFile | None = File(None),
    recognition_image: UploadFile | None = File(None),
    current_user: dict = Depends(get_current_user)
):
    """
    Обновление интерактивного объекта

    Args:
        object_id: ID объекта
        request: HTTP запрос
        db: Сессия базы данных
        name: Название объекта
        description: Описание объекта (HTML) - статья для отображения
        photo: Новое фото объекта для отображения (опционально)
        recognition_image: Новое изображение для распознавания (опционально, только для AR)
        current_user: Текущий пользователь

    Returns:
        RedirectResponse: Редирект на список объектов или JSON с ошибкой

    Raises:
        HTTPException: Если пользователь не администратор или объект не найден
    """
    user = get_user_by_username(db, current_user.get("username"))
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут редактировать объекты")

    obj = get_interactive_object_by_id(object_id, db)
    if not obj:
        raise HTTPException(status_code=404, detail="Объект не найден")

    # Валидация
    if not name or len(name.strip()) == 0:
        return JSONResponse(
            status_code=400,
            content={"detail": "Название не может быть пустым"}
        )

    old_photo_path = obj.photo
    old_recognition_image_path = obj.recognition_image
    new_photo_path = None
    new_recognition_image_path = None

    try:
        # Сохранение нового фото для отображения
        if photo and photo.filename:
            new_photo_path = save_file(photo, file_type="image")

        # Сохранение нового изображения для распознавания (только для AR)
        if recognition_image and recognition_image.filename:
            if obj.object_type != ObjectType.AR:
                return JSONResponse(
                    status_code=400,
                    content={"detail": "Изображение для распознавания доступно только для AR объектов"}
                )
            new_recognition_image_path = save_file(recognition_image, file_type="image")

        # Обновление объекта
        update_interactive_object(
            object_id=object_id,
            name=name.strip(),
            description=description if description else None,
            photo=new_photo_path if new_photo_path else obj.photo,
            recognition_image=new_recognition_image_path if new_recognition_image_path else obj.recognition_image,
            db=db
        )

        # Удаляем старые файлы только после успешного обновления
        if new_photo_path and old_photo_path:
            delete_file(old_photo_path)
        if new_recognition_image_path and old_recognition_image_path:
            delete_file(old_recognition_image_path)

        return RedirectResponse(url="/objects/manage", status_code=303)

    except Exception as e:
        # Удаляем новые загруженные файлы в случае ошибки
        if new_photo_path:
            delete_file(new_photo_path)
        if new_recognition_image_path:
            delete_file(new_recognition_image_path)

        return JSONResponse(
            status_code=500,
            content={"detail": f"Ошибка при обновлении объекта: {str(e)}"}
        )


@router.post("/{object_id}/delete", include_in_schema=False)
async def delete_object_route(
    object_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Удаление интерактивного объекта

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
        raise HTTPException(status_code=403, detail="Только администраторы могут удалять объекты")

    obj = get_interactive_object_by_id(object_id, db)
    if not obj:
        raise HTTPException(status_code=404, detail="Объект не найден")

    delete_interactive_object(object_id, db)

    return RedirectResponse(url="/objects/manage", status_code=303)


@router.get("/scanner", include_in_schema=False)
def scanner_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Страница сканера для пользователей

    Args:
        request: HTTP запрос
        db: Сессия базы данных
        current_user: Текущий пользователь

    Returns:
        HTMLResponse: HTML страница сканера

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
        "scanner.html",
        {
            "request": request,
            "current_user": user_info
        }
    )


@router.get("/api/ar-objects", include_in_schema=False)
def get_ar_objects_api(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    API для получения всех AR объектов для распознавания

    Args:
        db: Сессия базы данных
        current_user: Текущий пользователь

    Returns:
        JSONResponse: JSON со списком AR объектов

    Raises:
        HTTPException: Если пользователь не авторизован
    """
    ar_objects = get_ar_objects_for_recognition(db)
    objects_data = []

    for obj in ar_objects:
        objects_data.append({
            "id": obj.id,
            "name": obj.name,
            "recognition_image_url": f"/static/{obj.recognition_image}" if obj.recognition_image else None
        })

    return JSONResponse(content={"objects": objects_data})


@router.get("/debug", include_in_schema=False)
def debug_ar_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Страница диагностики AR объектов
    """
    user = get_user_by_username(db, current_user.get("username"))
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут просматривать диагностику")

    user_info = {
        "username": user.username,
        "is_admin": user.is_admin
    }

    return templates.TemplateResponse(
        "debug_ar.html",
        {
            "request": request,
            "current_user": user_info
        }
    )


@router.get("/api/debug/ar-objects", include_in_schema=False)
def debug_ar_objects(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Диагностический эндпоинт для проверки AR объектов
    """
    ar_objects = get_ar_objects_for_recognition(db)

    debug_info = {
        "total_ar_objects": len(ar_objects),
        "objects": []
    }

    for obj in ar_objects:
        has_orb = bool(obj.orb_keypoints and obj.orb_descriptors)
        debug_info["objects"].append({
            "id": obj.id,
            "name": obj.name,
            "has_orb_features": has_orb,
            "orb_keypoints_length": len(obj.orb_keypoints) if obj.orb_keypoints else 0,
            "orb_descriptors_length": len(obj.orb_descriptors) if obj.orb_descriptors else 0,
            "recognition_image": obj.recognition_image
        })

    return JSONResponse(content=debug_info)


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

    Raises:
        HTTPException: Если пользователь не авторизован или ошибка обработки
    """
    from app.services.orb_service import match_orb_features

    try:
        # Читаем изображение
        image_data = await image.read()

        if not image_data:
            print("⚠️ Получено пустое изображение")
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "Пустое изображение"}
            )

        print(f"📸 Получено изображение размером {len(image_data)} байт")

        # Получаем все AR объекты с ORB признаками
        ar_objects = get_ar_objects_for_recognition(db)
        print(f"📦 Найдено AR объектов в БД: {len(ar_objects)}")

        objects_with_orb = [obj for obj in ar_objects if obj.orb_keypoints and obj.orb_descriptors]
        print(f"✅ AR объектов с ORB признаками: {len(objects_with_orb)}")

        if len(objects_with_orb) == 0:
            print("⚠️ В базе нет AR объектов с ORB признаками!")
            return JSONResponse(content={
                "success": True,
                "matched": False,
                "message": "В базе нет AR объектов для распознавания"
            })

        best_match = None
        best_confidence = 0.0
        best_match_count = 0

        # Проверяем изображение против каждого объекта
        for obj in ar_objects:
            # Пропускаем объекты без ORB признаков
            if not obj.orb_keypoints or not obj.orb_descriptors:
                print(f"⏭️ Объект '{obj.name}' (ID: {obj.id}): пропущен (нет ORB признаков)")
                continue

            # Сопоставляем признаки
            matched, confidence, match_count = match_orb_features(
                query_image_data=image_data,
                target_keypoints_json=obj.orb_keypoints,
                target_descriptors_bytes=obj.orb_descriptors,
                min_match_count=10,
                ratio_threshold=0.75
            )

            print(f"🔍 Объект '{obj.name}' (ID: {obj.id}): matched={matched}, confidence={confidence:.2f}%, matches={match_count}")

            # Сохраняем лучший результат
            if matched and confidence > best_confidence:
                best_match = obj
                best_confidence = confidence
                best_match_count = match_count

        # Если найдено совпадение
        if best_match:
            result = {
                "success": True,
                "matched": True,
                "object_id": best_match.id,
                "object_name": best_match.name,
                "confidence": round(best_confidence, 2),
                "match_count": best_match_count,
                "content": {
                    "id": best_match.id,
                    "name": best_match.name,
                    "description": best_match.description,
                    "photo": best_match.photo
                }
            }

            print(f"✅ Найдено совпадение: {best_match.name} с уверенностью {best_confidence:.2f}%")
            return JSONResponse(content=result)

        # Совпадение не найдено
        print(f"❌ Изображение не распознано. Проверено объектов: {len(objects_with_orb)}")
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


@router.get("/api/search-qr")
def search_by_qr_string(
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
    obj = get_interactive_object_by_qr_string(qr_string, db)
    if not obj:
        raise HTTPException(status_code=404, detail="QR объект не найден")

    object_dict = interactive_object_to_dict(obj)

    return JSONResponse(content={
        "success": True,
        "data": object_dict
    })


@router.get("/view/{object_id}", include_in_schema=False)
def view_object(
    object_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    Просмотр объекта (публичная страница, доступна без авторизации)

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
    obj = get_interactive_object_by_id(object_id, db)
    if not obj:
        raise HTTPException(status_code=404, detail="Объект не найден")

    object_dict = interactive_object_to_dict(obj)

    return templates.TemplateResponse(
        "object_view.html",
        {
            "request": request,
            "object": object_dict,
            "current_user": current_user
        }
    )

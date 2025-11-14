"""
Router for working with knowledge base articles
"""
from fastapi import APIRouter, Request, Form, UploadFile, File, HTTPException, Depends
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.article_models import Article
from app.services.knowledge_base_utils import (
    create_article,
    read_articles,
    read_article_by_id,
    update_article,
    delete_article
)
from app.services.file_utils import save_file, delete_file
from app.services.auth import get_current_user, get_current_user_optional
from app.services.user_service import get_user_by_username
from app.services.article_service import search_articles as db_search_articles

router = APIRouter(prefix="/knowledge_base", tags=["knowledge-base"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", include_in_schema=False)
def list_articles(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    List of all articles

    Args:
        request: HTTP request
        db: Database session
        current_user: Current user

    Returns:
        HTMLResponse: HTML page with articles list

    Raises:
        HTTPException: If user not authorized
    """
    articles = read_articles(db)
    
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
            "articles": articles,
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
    Article creation form

    Args:
        request: HTTP request
        db: Database session
        current_user: Current user

    Returns:
        HTMLResponse: HTML page with creation form

    Raises:
        HTTPException: If user is not admin or not authorized
    """
    user = get_user_by_username(db, current_user.get("username"))
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Only admins can create articles")
    
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
    API for searching articles

    Args:
        q: Search query
        db: Database session
        current_user: Current user

    Returns:
        JSONResponse: JSON with search results

    Raises:
        HTTPException: If user not authorized
    """
    if not q:
        articles = read_articles(db)
        return JSONResponse(content={"articles": articles})

    # Use database search
    db_articles = db_search_articles(db, q)
    articles = [
        {
            "id": a.id,
            "title": a.title,
            "text": a.text,
            "photo": a.photo,
            "video": a.video,
            "created_by": a.created_by,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "updated_at": a.updated_at.isoformat() if a.updated_at else None
        }
        for a in db_articles
    ]

    return JSONResponse(content={"articles": articles})


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
    Create new article

    Args:
        request: HTTP request
        db: Database session
        title: Article title
        text: Article text
        photo: Photo file (optional)
        video: Video file (optional)
        current_user: Current user

    Returns:
        RedirectResponse: Redirect to articles list or JSON with error

    Raises:
        HTTPException: If user is not admin or validation error
    """
    user = get_user_by_username(db, current_user.get("username"))
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Only admins can create articles")

    # Validate title
    if not title or len(title.strip()) == 0:
        return JSONResponse(
            status_code=400,
            content={"detail": "Title cannot be empty"}
        )

    photo_path = None
    video_path = None

    try:
        # Save files
        if photo and photo.filename:
            photo_path = save_file(photo, file_type="image")

        if video and video.filename:
            video_path = save_file(video, file_type="video")

        # Create article
        # For HTML content don't use strip() to preserve formatting
        article = Article(
            id=0,  # id is assigned in service
            title=title.strip(),
            text=text if text else None,  # Save HTML content as is
            photo=photo_path,
            video=video_path
        )
        create_article(article, db, created_by=user.username)
        
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
            content={"detail": f"Error creating article: {str(e)}"}
        )


@router.get("/{article_id}", include_in_schema=False)
def article_detail(
    request: Request,
    article_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Article detail page

    Args:
        request: HTTP request
        article_id: Article ID
        db: Database session
        current_user: Current user

    Returns:
        HTMLResponse: HTML page with article details

    Raises:
        HTTPException: If article not found or user not authorized
    """
    article = read_article_by_id(article_id, db)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
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
            "article": article,
            "current_user": user_info
        }
    )


@router.get("/{article_id}/edit", include_in_schema=False)
def edit_form(
    request: Request,
    article_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Article edit form

    Args:
        request: HTTP request
        article_id: Article ID
        db: Database session
        current_user: Current user

    Returns:
        HTMLResponse: HTML page with edit form

    Raises:
        HTTPException: If user is not admin or article not found
    """
    user = get_user_by_username(db, current_user.get("username"))
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Only admins can edit articles")

    article = read_article_by_id(article_id, db)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    user_info = {
        "username": user.username,
        "is_admin": user.is_admin
    }
    
    return templates.TemplateResponse(
        "edit_material.html",
        {
            "request": request,
            "article": article,
            "current_user": user_info
        }
    )


@router.post("/{article_id}/edit", include_in_schema=False)
async def submit_edit(
    request: Request,
    article_id: int,
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
    Edit existing article

    Args:
        request: HTTP request
        article_id: Article ID
        db: Database session
        title: Article title
        text: Article text
        photo: New photo file (optional)
        video: New video file (optional)
        remove_photo: Remove photo flag
        remove_video: Remove video flag
        current_user: Current user

    Returns:
        RedirectResponse: Redirect to article detail page

    Raises:
        HTTPException: If user is not admin or article not found
    """
    user = get_user_by_username(db, current_user.get("username"))
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Only admins can edit articles")

    article = read_article_by_id(article_id, db)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    # Validate title
    if not title or len(title.strip()) == 0:
        raise HTTPException(status_code=400, detail="Title cannot be empty")
    
    updated_data = {
        "title": title.strip(), 
        "text": text if text else None  # HTML контент сохраняем как есть
    }
    
    # Remove photo
    if remove_photo == "true" and article.get("photo"):
        delete_file(article["photo"])
        updated_data["photo"] = None

    # Remove video
    if remove_video == "true" and article.get("video"):
        delete_file(article["video"])
        updated_data["video"] = None

    # Upload new photo
    if photo and photo.filename:
        new_photo = save_file(photo, file_type="image")
        if new_photo:
            # Remove old photo
            if article.get("photo"):
                delete_file(article["photo"])
            updated_data["photo"] = new_photo

    # Upload new video
    if video and video.filename:
        new_video = save_file(video, file_type="video")
        if new_video:
            # Remove old video
            if article.get("video"):
                delete_file(article["video"])
            updated_data["video"] = new_video

    update_article(article_id, updated_data, db)
    return RedirectResponse(url=f"/knowledge_base/{article_id}", status_code=303)


@router.post("/{article_id}/delete", include_in_schema=False)
async def delete_article_route(
    article_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete article

    Args:
        article_id: Article ID
        db: Database session
        current_user: Current user

    Returns:
        RedirectResponse: Redirect to articles list

    Raises:
        HTTPException: If user is not admin or article not found
    """
    user = get_user_by_username(db, current_user.get("username"))
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Only admins can delete articles")

    article = read_article_by_id(article_id, db)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    # Delete files
    if article.get("photo"):
        delete_file(article["photo"])

    if article.get("video"):
        delete_file(article["video"])

    delete_article(article_id, db)
    return RedirectResponse(url="/knowledge_base/", status_code=303)

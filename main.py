"""
Главный файл приложения FastAPI
"""
from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from app.routers import materials_router, auth_router, chatbot_router, scanner_router, interactive_object_router
from app.database import init_db, get_db
from app.init_db import init_database
from app.services.auth import get_current_user_optional
from app.services.user_service import get_user_by_username
from typing import Optional
from sqlalchemy.orm import Session

app = FastAPI(title="Knowledge Base")
templates = Jinja2Templates(directory="app/templates")


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Обработчик HTTP исключений для редиректа неавторизованных пользователей
    
    Args:
        request: HTTP запрос
        exc: HTTP исключение
    
    Returns:
        RedirectResponse для HTML запросов с 401, JSON для API запросов
    """
    # Если это ошибка авторизации (401)
    if exc.status_code == status.HTTP_401_UNAUTHORIZED:
        # Проверяем, является ли запрос API запросом
        is_api_request = (
            request.url.path.startswith("/api/") or
            "application/json" in request.headers.get("accept", "").lower() or
            request.headers.get("content-type", "").lower() == "application/json" or
            getattr(request.state, "is_api_request", False)
        )
        
        # Для HTML запросов делаем редирект на страницу авторизации
        if not is_api_request:
            return RedirectResponse(url="/auth/", status_code=303)
    
    # Для API запросов или других ошибок возвращаем стандартный ответ
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


@app.on_event("startup")
async def startup_event():
    """
    Инициализация БД при запуске приложения
    """
    try:
        init_database()
    except Exception as e:
        print(f"Предупреждение: Ошибка при инициализации БД: {e}")


# Монтируем папку статики
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Подключаем маршруты
app.include_router(materials_router.router)
app.include_router(auth_router.router)
app.include_router(chatbot_router.router)
app.include_router(scanner_router.router)
app.include_router(interactive_object_router.router)

@app.get("/", include_in_schema=False)
def root():
    """
    Редирект на главную страницу базы знаний
    
    Returns:
        RedirectResponse: Редирект на /knowledge_base/
    """
    return RedirectResponse(url="/knowledge_base/")


@app.get("/profile", response_class=HTMLResponse, name="profile_page_main")
def profile_page_main(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    Страница профиля пользователя (альтернативный маршрут)
    
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
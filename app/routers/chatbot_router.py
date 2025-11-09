"""
Роутер для чат-бота
"""
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict
from app.database import get_db
from app.services.auth import get_current_user, get_current_user_optional
from app.services.user_service import get_user_by_username
from app.services.chatbot_service import get_chatbot_response
from app.services.chat_service import (
    create_chat_session,
    get_chat_session_by_id,
    get_user_chat_sessions,
    delete_chat_session,
    add_chat_message,
    get_chat_messages,
    get_conversation_history
)

router = APIRouter(prefix="/chatbot", tags=["chatbot"])
templates = Jinja2Templates(directory="app/templates")


class ChatMessageRequest(BaseModel):
    """
    Модель запроса сообщения чата
    """
    message: str
    chat_id: Optional[int] = None
    conversation_history: Optional[List[Dict[str, str]]] = None


class CreateChatRequest(BaseModel):
    """
    Модель запроса создания чата
    """
    title: Optional[str] = "Новый чат"


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def chatbot_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Страница чат-бота
    
    Args:
        request: HTTP запрос
        db: Сессия базы данных
        current_user: Текущий пользователь
    
    Returns:
        HTMLResponse: HTML страница чат-бота
    
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
        "chatbot.html",
        {
            "request": request,
            "current_user": user_info
        }
    )


@router.get("/api/chats", response_class=JSONResponse)
def get_chats(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Получить все чаты пользователя
    
    Args:
        db: Сессия базы данных
        current_user: Текущий пользователь
    
    Returns:
        JSONResponse: JSON со списком чатов
    
    Raises:
        HTTPException: Если пользователь не авторизован
    """
    user = get_user_by_username(db, current_user.get("username"))
    if not user or not user.is_active:
        raise HTTPException(status_code=403, detail="Пользователь не авторизован")
    
    user_id = user.id
    chat_sessions = get_user_chat_sessions(db, user_id)
    
    return JSONResponse(content={
        "chats": [
            {
                "id": chat.id,
                "title": chat.title,
                "created_at": chat.created_at.isoformat() if chat.created_at else None,
                "updated_at": chat.updated_at.isoformat() if chat.updated_at else None
            }
            for chat in chat_sessions
        ]
    })


@router.post("/api/chats", response_class=JSONResponse)
def create_chat(
    request: CreateChatRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Создать новый чат
    
    Args:
        request: Данные для создания чата
        db: Сессия базы данных
        current_user: Текущий пользователь
    
    Returns:
        JSONResponse: JSON с данными созданного чата
    
    Raises:
        HTTPException: Если пользователь не авторизован
    """
    user = get_user_by_username(db, current_user.get("username"))
    if not user or not user.is_active:
        raise HTTPException(status_code=403, detail="Пользователь не авторизован")
    
    user_id = user.id
    chat_session = create_chat_session(db, user_id, request.title)
    
    return JSONResponse(content={
        "id": chat_session.id,
        "title": chat_session.title,
        "created_at": chat_session.created_at.isoformat() if chat_session.created_at else None
    })


@router.get("/api/chats/{chat_id}", response_class=JSONResponse)
def get_chat(
    chat_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Получить чат с сообщениями
    
    Args:
        chat_id: ID чата
        db: Сессия базы данных
        current_user: Текущий пользователь
    
    Returns:
        JSONResponse: JSON с данными чата и сообщениями
    
    Raises:
        HTTPException: Если чат не найден или пользователь не авторизован/не владелец
    """
    user = get_user_by_username(db, current_user.get("username"))
    if not user or not user.is_active:
        raise HTTPException(status_code=403, detail="Пользователь не авторизован")
    
    user_id = user.id
    chat_session = get_chat_session_by_id(db, chat_id, user_id)
    if not chat_session:
        raise HTTPException(status_code=404, detail="Чат не найден или у вас нет доступа к этому чату")
    
    messages = get_chat_messages(db, chat_id)
    
    return JSONResponse(content={
        "id": chat_session.id,
        "title": chat_session.title,
        "created_at": chat_session.created_at.isoformat() if chat_session.created_at else None,
        "updated_at": chat_session.updated_at.isoformat() if chat_session.updated_at else None,
        "messages": [
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at.isoformat() if msg.created_at else None
            }
            for msg in messages
        ]
    })


@router.delete("/api/chats/{chat_id}", response_class=JSONResponse)
def delete_chat(
    chat_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Удалить чат
    
    Args:
        chat_id: ID чата
        db: Сессия базы данных
        current_user: Текущий пользователь
    
    Returns:
        JSONResponse: JSON с результатом удаления
    
    Raises:
        HTTPException: Если чат не найден или пользователь не авторизован/не владелец
    """
    user = get_user_by_username(db, current_user.get("username"))
    if not user or not user.is_active:
        raise HTTPException(status_code=403, detail="Пользователь не авторизован")
    
    user_id = user.id
    success = delete_chat_session(db, chat_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Чат не найден или у вас нет доступа к этому чату")
    
    return JSONResponse(content={"success": True})


@router.post("/api/chat", response_class=JSONResponse)
async def chat_api(
    chat_message: ChatMessageRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    API endpoint для отправки сообщений чат-боту
    
    Args:
        chat_message: Сообщение пользователя и ID чата
        db: Сессия базы данных
        current_user: Текущий пользователь
    
    Returns:
        JSON с ответом чат-бота
    
    Raises:
        HTTPException: Если пользователь не авторизован или нет доступа к чату
    """
    if not chat_message.message or len(chat_message.message.strip()) == 0:
        raise HTTPException(status_code=400, detail="Сообщение не может быть пустым")
    
    user = get_user_by_username(db, current_user.get("username"))
    if not user or not user.is_active:
        raise HTTPException(status_code=403, detail="Пользователь не авторизован")
    
    user_id = user.id
    
    # Получаем или создаем чат
    chat_id = chat_message.chat_id
    if not chat_id:
        chat_session = create_chat_session(db, user_id)
        chat_id = chat_session.id
    else:
        # Проверяем, что чат существует и принадлежит пользователю
        chat_session = get_chat_session_by_id(db, chat_id, user_id)
        if not chat_session:
            raise HTTPException(status_code=404, detail="Чат не найден или у вас нет доступа к этому чату")
    
    # Сохраняем сообщение пользователя
    add_chat_message(db, chat_id, "user", chat_message.message)
    
    # Получаем историю разговора из БД, если не передана
    conversation_history = chat_message.conversation_history
    if not conversation_history:
        conversation_history = get_conversation_history(db, chat_id)
    
    # Получаем ответ от чат-бота
    result = await get_chatbot_response(
        user_query=chat_message.message,
        db=db,
        conversation_history=conversation_history
    )
    
    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])
    
    # Сохраняем ответ бота
    add_chat_message(db, chat_id, "assistant", result["response"])
    
    return JSONResponse(content={
        "response": result["response"],
        "materials_used": result.get("materials_used", 0),
        "chat_id": chat_id
    })


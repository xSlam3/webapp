"""
Сервис для работы с чатами в БД
"""
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models.chat_db_models import ChatSession, ChatMessage
from typing import Optional, List


def create_chat_session(db: Session, user_id: Optional[int] = None, title: str = "Новый чат") -> ChatSession:
    """
    Создать новую сессию чата
    
    Args:
        db: Сессия базы данных
        user_id: ID пользователя (опционально)
        title: Заголовок чата
    
    Returns:
        ChatSession: Созданная сессия чата
    """
    chat_session = ChatSession(
        user_id=user_id,
        title=title
    )
    db.add(chat_session)
    db.commit()
    db.refresh(chat_session)
    return chat_session


def get_chat_session_by_id(db: Session, chat_id: int, user_id: Optional[int] = None) -> Optional[ChatSession]:
    """
    Получить сессию чата по ID
    
    Args:
        db: Сессия базы данных
        chat_id: ID чата
        user_id: ID пользователя для проверки прав (обязательно для безопасности)
    
    Returns:
        Optional[ChatSession]: Сессия чата или None если не найдена или не принадлежит пользователю
    """
    query = db.query(ChatSession).filter(ChatSession.id == chat_id)
    if user_id is not None:
        query = query.filter(ChatSession.user_id == user_id)
    else:
        # Если user_id не передан, возвращаем None для безопасности
        return None
    return query.first()


def get_user_chat_sessions(db: Session, user_id: Optional[int] = None, limit: int = 100) -> List[ChatSession]:
    """
    Получить все сессии чата пользователя
    
    Args:
        db: Сессия базы данных
        user_id: ID пользователя (обязательно для безопасности)
        limit: Максимальное количество записей
    
    Returns:
        List[ChatSession]: Список сессий чата пользователя
    """
    if user_id is None:
        # Если user_id не передан, возвращаем пустой список для безопасности
        return []
    query = db.query(ChatSession).filter(ChatSession.user_id == user_id)
    return query.order_by(desc(ChatSession.updated_at)).limit(limit).all()


def update_chat_session_title(db: Session, chat_id: int, title: str, user_id: Optional[int] = None) -> Optional[ChatSession]:
    """
    Обновить заголовок сессии чата
    
    Args:
        db: Сессия базы данных
        chat_id: ID чата
        title: Новый заголовок
        user_id: ID пользователя для проверки прав (опционально)
    
    Returns:
        Optional[ChatSession]: Обновленная сессия чата или None
    """
    chat_session = get_chat_session_by_id(db, chat_id, user_id)
    if not chat_session:
        return None
    
    chat_session.title = title
    # updated_at обновится автоматически через onupdate в модели
    db.commit()
    db.refresh(chat_session)
    return chat_session


def delete_chat_session(db: Session, chat_id: int, user_id: Optional[int] = None) -> bool:
    """
    Удалить сессию чата (сообщения удалятся каскадно)
    
    Args:
        db: Сессия базы данных
        chat_id: ID чата
        user_id: ID пользователя для проверки прав (опционально)
    
    Returns:
        bool: True если удаление успешно
    """
    chat_session = get_chat_session_by_id(db, chat_id, user_id)
    if not chat_session:
        return False
    
    db.delete(chat_session)
    db.commit()
    return True


def add_chat_message(db: Session, chat_session_id: int, role: str, content: str) -> ChatMessage:
    """
    Добавить сообщение в сессию чата
    
    Args:
        db: Сессия базы данных
        chat_session_id: ID сессии чата
        role: Роль отправителя (user/assistant)
        content: Содержание сообщения
    
    Returns:
        ChatMessage: Созданное сообщение
    """
    chat_message = ChatMessage(
        chat_session_id=chat_session_id,
        role=role,
        content=content
    )
    db.add(chat_message)
    
    # Обновляем заголовок сессии, если это первое сообщение пользователя
    # Используем прямой запрос, так как user_id не нужен для обновления заголовка
    chat_session = db.query(ChatSession).filter(ChatSession.id == chat_session_id).first()
    if chat_session and role == 'user':
        if not chat_session.title or chat_session.title == "Новый чат":
            title = content[:50] + ("..." if len(content) > 50 else "")
            chat_session.title = title
        # Обновляем updated_at, чтобы сессия была помечена как обновленная
        # onupdate сработает автоматически при коммите
    
    db.commit()
    db.refresh(chat_message)
    return chat_message


def get_chat_messages(db: Session, chat_session_id: int, limit: int = 1000) -> List[ChatMessage]:
    """
    Получить все сообщения сессии чата
    
    Args:
        db: Сессия базы данных
        chat_session_id: ID сессии чата
        limit: Максимальное количество сообщений
    
    Returns:
        List[ChatMessage]: Список сообщений
    """
    return db.query(ChatMessage).filter(
        ChatMessage.chat_session_id == chat_session_id
    ).order_by(ChatMessage.created_at).limit(limit).all()


def get_conversation_history(db: Session, chat_session_id: int) -> List[dict]:
    """Получить историю разговора в формате для API"""
    messages = get_chat_messages(db, chat_session_id)
    return [
        {
            "role": msg.role,
            "content": msg.content
        }
        for msg in messages
    ]


"""
Сервис для работы с чат-ботом на основе OpenRouter API
"""
import httpx
import re
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from app.config import settings
from app.services.material_service import semantic_search_materials, search_materials, get_all_materials


def format_materials_as_context(materials: List) -> str:
    """Форматирует материалы в контекст для промпта"""
    if not materials:
        return "В базе знаний пока нет материалов."
    
    context_parts = ["Документация из базы знаний:\n"]
    for i, material in enumerate(materials, 1):
        context_parts.append(f"\n--- Материал {i} ---")
        context_parts.append(f"Заголовок: {material.title}")
        if material.text:
            # Ограничиваем длину текста, чтобы не превысить лимиты токенов
            text = material.text[:2000] if len(material.text) > 2000 else material.text
            context_parts.append(f"Содержание: {text}")
    
    return "\n".join(context_parts)


def search_relevant_materials(db: Session, query: str, limit: int = 5) -> List:
    """
    Ищет релевантные материалы по запросу пользователя используя семантический поиск
    """
    if not query or len(query.strip()) == 0:
        # Если запрос пустой, возвращаем последние материалы
        return get_all_materials(db, skip=0, limit=limit)

    # НОВОЕ: Используем семантический поиск вместо простого текстового
    materials = semantic_search_materials(db, query, limit=limit, threshold=0.25)

    # Если семантический поиск ничего не нашел, пробуем обычный текстовый поиск
    if len(materials) == 0:
        materials = search_materials(db, query)[:limit]

    # Если найдено меньше материалов, дополняем последними
    if len(materials) < limit:
        all_materials = get_all_materials(db, skip=0, limit=limit * 2)
        # Добавляем материалы, которых еще нет в результатах
        existing_ids = {m.id for m in materials}
        for material in all_materials:
            if material.id not in existing_ids and len(materials) < limit:
                materials.append(material)

    return materials[:limit]


async def get_chatbot_response(
    user_query: str,
    db: Session,
    conversation_history: Optional[List[Dict[str, str]]] = None
) -> Dict[str, Any]:
    """
    Получает ответ от чат-бота на основе запроса пользователя и документации
    
    Args:
        user_query: Запрос пользователя
        db: Сессия базы данных
        conversation_history: История разговора (опционально)
    
    Returns:
        Словарь с ответом и метаданными
    """
    if not settings.OPENROUTER_API_KEY:
        return {
            "error": "OpenRouter API key не настроен. Пожалуйста, добавьте OPENROUTER_API_KEY в .env файл.",
            "response": None
        }
    
    # Ищем релевантные материалы
    relevant_materials = search_relevant_materials(db, user_query)
    context = format_materials_as_context(relevant_materials)
    
    # Формируем системный промпт
    system_prompt = """Ты - полезный ассистент, который помогает пользователям находить информацию в базе знаний.
Используй предоставленную документацию для ответа на вопросы пользователя.
ВАЖНО: 
- Отвечай полным, развернутым ответом на основе документации
- НЕ предоставляй ссылки или URL
- НЕ упоминай номера материалов или заголовки как ссылки
- Просто отвечай на вопрос, используя информацию из документации
- Если информация не найдена в документации, честно скажи об этом
- Отвечай на русском языке, кратко, но информативно"""
    
    # Формируем промпт с контекстом
    user_prompt = f"""Ниже представлена документация из базы знаний:

{context}

---

Вопрос пользователя: {user_query}

Пожалуйста, ответь на вопрос пользователя, используя ТОЛЬКО информацию из документации выше. 
Отвечай полным ответом, не упоминая ссылки или номера материалов."""
    
    # Формируем сообщения для API
    messages = [{"role": "system", "content": system_prompt}]
    
    # Добавляем историю разговора, если есть
    if conversation_history:
        for msg in conversation_history[-10:]:  # Ограничиваем историю последними 10 сообщениями
            messages.append(msg)
    
    # Добавляем текущий запрос
    messages.append({"role": "user", "content": user_prompt})
    
    # Вызываем OpenRouter API
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                settings.OPENROUTER_API_URL,
                headers={
                    "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "http://localhost:8000",  # Опционально, для отслеживания
                    "X-Title": "Knowledge Base Chatbot"  # Опционально
                },
                json={
                    "model": settings.OPENROUTER_MODEL,
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 1000
                }
            )
            response.raise_for_status()
            data = response.json()
            
            # Извлекаем ответ
            if "choices" in data and len(data["choices"]) > 0:
                assistant_message = data["choices"][0]["message"]["content"]
                
                # Очищаем ответ от возможных ссылок и лишних упоминаний
                # Удаляем markdown ссылки вида [текст](url)
                assistant_message = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', assistant_message)
                # Удаляем обычные URL
                assistant_message = re.sub(r'https?://\S+', '', assistant_message)
                # Удаляем упоминания "Материал N" как ссылки
                assistant_message = re.sub(r'Материал\s+\d+[:\s]*', '', assistant_message, flags=re.IGNORECASE)
                # Убираем лишние пробелы
                assistant_message = ' '.join(assistant_message.split())
                
                return {
                    "response": assistant_message,
                    "error": None,
                    "materials_used": len(relevant_materials)
                }
            else:
                return {
                    "error": "Неожиданный формат ответа от API",
                    "response": None
                }
    
    except httpx.HTTPStatusError as e:
        error_msg = f"Ошибка API: {e.response.status_code}"
        try:
            error_data = e.response.json()
            if "error" in error_data:
                error_msg = error_data["error"].get("message", error_msg)
        except:
            pass
        
        return {
            "error": error_msg,
            "response": None
        }
    
    except httpx.TimeoutException:
        return {
            "error": "Превышено время ожидания ответа от API",
            "response": None
        }
    
    except Exception as e:
        return {
            "error": f"Ошибка при обращении к API: {str(e)}",
            "response": None
        }


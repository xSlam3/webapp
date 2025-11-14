"""
Service for working with chatbot based on OpenRouter API
"""
import httpx
import re
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from app.config import settings
from app.services.article_service import semantic_search_articles, search_articles, get_all_articles


def format_articles_as_context(articles: List) -> str:
    """Formats articles into context for prompt"""
    if not articles:
        return "There are no articles in the knowledge base yet."

    context_parts = ["Documentation from knowledge base:\n"]
    for i, article in enumerate(articles, 1):
        context_parts.append(f"\n--- Article {i} ---")
        context_parts.append(f"Title: {article.title}")
        if article.text:
            # Limit text length to avoid token limits
            text = article.text[:2000] if len(article.text) > 2000 else article.text
            context_parts.append(f"Content: {text}")

    return "\n".join(context_parts)


def search_relevant_articles(db: Session, query: str, limit: int = 5) -> List:
    """
    Searches for relevant articles by user query using semantic search
    """
    if not query or len(query.strip()) == 0:
        # If query is empty, return latest articles
        return get_all_articles(db, skip=0, limit=limit)

    # Use semantic search instead of simple text search
    articles = semantic_search_articles(db, query, limit=limit, threshold=0.25)

    # If semantic search found nothing, try regular text search
    if len(articles) == 0:
        articles = search_articles(db, query)[:limit]

    # If found less articles, supplement with latest ones
    if len(articles) < limit:
        all_articles = get_all_articles(db, skip=0, limit=limit * 2)
        # Add articles that are not yet in results
        existing_ids = {a.id for a in articles}
        for article in all_articles:
            if article.id not in existing_ids and len(articles) < limit:
                articles.append(article)

    return articles[:limit]


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
    
    # Search for relevant articles
    relevant_articles = search_relevant_articles(db, user_query)
    context = format_articles_as_context(relevant_articles)
    
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
                    "articles_used": len(relevant_articles)
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


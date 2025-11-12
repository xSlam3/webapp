"""
Сервис для работы с векторными эмбеддингами текста
"""
from sentence_transformers import SentenceTransformer
import json
import numpy as np
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

# Глобальная переменная для хранения модели (загружается один раз)
_model: Optional[SentenceTransformer] = None


def get_embedding_model() -> SentenceTransformer:
    """
    Получить модель для генерации эмбеддингов (singleton)
    Использует легковесную мультиязычную модель с поддержкой русского языка
    """
    global _model
    if _model is None:
        logger.info("Загрузка модели sentence-transformers...")
        # Используем легковесную модель с поддержкой русского языка
        _model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        logger.info("Модель успешно загружена")
    return _model


def generate_embedding(text: str) -> List[float]:
    """
    Генерирует векторное представление текста

    Args:
        text: Текст для преобразования в вектор

    Returns:
        List[float]: Векторное представление текста
    """
    if not text or len(text.strip()) == 0:
        return []

    try:
        model = get_embedding_model()
        embedding = model.encode(text, convert_to_tensor=False)
        # Конвертируем numpy array в список
        return embedding.tolist()
    except Exception as e:
        logger.error(f"Ошибка при генерации эмбеддинга: {e}")
        return []


def generate_material_embedding(title: str, text: Optional[str] = None) -> str:
    """
    Генерирует эмбеддинг для материала (комбинирует заголовок и текст)

    Args:
        title: Заголовок материала
        text: Текст материала (опционально)

    Returns:
        str: JSON строка с векторным представлением
    """
    # Комбинируем заголовок и текст для лучшего контекста
    combined_text = title
    if text:
        # Ограничиваем текст для экономии памяти и скорости
        text_preview = text[:1000] if len(text) > 1000 else text
        combined_text = f"{title}. {text_preview}"

    embedding = generate_embedding(combined_text)

    # Сохраняем как JSON строку
    return json.dumps(embedding) if embedding else None


def embedding_from_json(embedding_json: str) -> Optional[np.ndarray]:
    """
    Преобразует JSON строку эмбеддинга в numpy array

    Args:
        embedding_json: JSON строка с вектором

    Returns:
        Optional[np.ndarray]: Numpy array или None
    """
    if not embedding_json:
        return None

    try:
        embedding_list = json.loads(embedding_json)
        return np.array(embedding_list)
    except Exception as e:
        logger.error(f"Ошибка при парсинге эмбеддинга: {e}")
        return None


def cosine_similarity(embedding1: np.ndarray, embedding2: np.ndarray) -> float:
    """
    Вычисляет косинусное сходство между двумя векторами

    Args:
        embedding1: Первый вектор
        embedding2: Второй вектор

    Returns:
        float: Косинусное сходство (от -1 до 1, чем ближе к 1, тем более похожи)
    """
    if embedding1 is None or embedding2 is None:
        return 0.0

    try:
        # Косинусное сходство = скалярное произведение / (норма1 * норма2)
        dot_product = np.dot(embedding1, embedding2)
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))
    except Exception as e:
        logger.error(f"Ошибка при вычислении косинусного сходства: {e}")
        return 0.0

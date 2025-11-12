"""
Сервис для работы с материалами в БД
"""
from sqlalchemy.orm import Session
from app.models.material_db_models import Material
from app.services.embedding_service import (
    generate_material_embedding,
    generate_embedding,
    embedding_from_json,
    cosine_similarity
)
from typing import Optional, List, Tuple
import logging

logger = logging.getLogger(__name__)


def create_material(db: Session, title: str, text: Optional[str] = None,
                   photo: Optional[str] = None, video: Optional[str] = None,
                   created_by: Optional[str] = None) -> Material:
    """
    Создать новый материал

    Args:
        db: Сессия базы данных
        title: Заголовок материала
        text: Текст материала
        photo: Путь к фото
        video: Путь к видео
        created_by: Имя создателя

    Returns:
        Material: Созданный материал
    """
    # Генерируем эмбеддинг для нового материала
    embedding = generate_material_embedding(title, text)

    material = Material(
        title=title,
        text=text,
        photo=photo,
        video=video,
        created_by=created_by,
        embedding=embedding
    )
    db.add(material)
    db.commit()
    db.refresh(material)
    return material


def get_material_by_id(db: Session, material_id: int) -> Optional[Material]:
    """
    Получить материал по ID
    
    Args:
        db: Сессия базы данных
        material_id: ID материала
    
    Returns:
        Optional[Material]: Материал или None
    """
    return db.query(Material).filter(Material.id == material_id).first()


def get_all_materials(db: Session, skip: int = 0, limit: int = 100) -> List[Material]:
    """
    Получить все материалы
    
    Args:
        db: Сессия базы данных
        skip: Количество пропущенных записей
        limit: Максимальное количество записей
    
    Returns:
        List[Material]: Список материалов
    """
    return db.query(Material).offset(skip).limit(limit).all()


def update_material(db: Session, material: Material, **kwargs) -> Material:
    """
    Обновить материал

    Args:
        db: Сессия базы данных
        material: Материал для обновления
        **kwargs: Поля для обновления

    Returns:
        Material: Обновленный материал
    """
    # Проверяем, изменились ли title или text - нужно перегенерировать эмбеддинг
    regenerate_embedding = False
    if 'title' in kwargs or 'text' in kwargs:
        regenerate_embedding = True

    for key, value in kwargs.items():
        if value is not None or key in ['photo', 'video']:  # Разрешаем установку None для фото/видео
            setattr(material, key, value)

    # Перегенерируем эмбеддинг если изменился контент
    if regenerate_embedding:
        new_embedding = generate_material_embedding(material.title, material.text)
        material.embedding = new_embedding

    db.commit()
    db.refresh(material)
    return material


def delete_material(db: Session, material: Material) -> bool:
    """
    Удалить материал
    
    Args:
        db: Сессия базы данных
        material: Материал для удаления
    
    Returns:
        bool: True если удаление успешно
    """
    db.delete(material)
    db.commit()
    return True


def search_materials(db: Session, query: str) -> List[Material]:
    """
    Поиск материалов по заголовку и тексту (простой текстовый поиск)

    Args:
        db: Сессия базы данных
        query: Поисковый запрос

    Returns:
        List[Material]: Список найденных материалов
    """
    search_term = f"%{query.lower()}%"
    return db.query(Material).filter(
        (Material.title.ilike(search_term)) |
        (Material.text.ilike(search_term))
    ).all()


def semantic_search_materials(db: Session, query: str, limit: int = 10, threshold: float = 0.3) -> List[Material]:
    """
    Семантический поиск материалов по векторному сходству

    Args:
        db: Сессия базы данных
        query: Поисковый запрос
        limit: Максимальное количество результатов
        threshold: Минимальный порог схожести (0-1)

    Returns:
        List[Material]: Список материалов, отсортированных по релевантности
    """
    try:
        # Генерируем эмбеддинг для поискового запроса
        query_embedding = generate_embedding(query)
        if not query_embedding:
            logger.warning("Не удалось создать эмбеддинг для запроса, используем обычный поиск")
            return search_materials(db, query)[:limit]

        # Получаем все материалы с эмбеддингами
        all_materials = db.query(Material).filter(Material.embedding.isnot(None)).all()

        if not all_materials:
            logger.warning("В БД нет материалов с эмбеддингами, используем обычный поиск")
            return search_materials(db, query)[:limit]

        # Вычисляем сходство для каждого материала
        materials_with_similarity: List[Tuple[Material, float]] = []

        import numpy as np
        query_emb_array = np.array(query_embedding)

        for material in all_materials:
            if material.embedding:
                material_emb_array = embedding_from_json(material.embedding)
                if material_emb_array is not None:
                    similarity = cosine_similarity(query_emb_array, material_emb_array)
                    if similarity >= threshold:
                        materials_with_similarity.append((material, similarity))

        # Сортируем по убыванию сходства
        materials_with_similarity.sort(key=lambda x: x[1], reverse=True)

        # Возвращаем топ результатов
        result = [material for material, _ in materials_with_similarity[:limit]]

        logger.info(f"Семантический поиск: найдено {len(result)} материалов для запроса '{query}'")
        return result

    except Exception as e:
        logger.error(f"Ошибка при семантическом поиске: {e}")
        # В случае ошибки возвращаем результат обычного поиска
        return search_materials(db, query)[:limit]


"""
Настройка базы данных SQLAlchemy
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

# Создаем движок БД
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

# Создаем фабрику сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Базовый класс для моделей
Base = declarative_base()


def get_db():
    """
    Dependency для получения сессии БД
    
    Yields:
        Session: Сессия базы данных
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Инициализация БД - создание всех таблиц
    """
    from app.models import user_db_models, material_db_models, chat_db_models, ar_tag_db_models, qr_object_db_models, interactive_object_db_models
    # Импортируем модели для регистрации в Base
    Base.metadata.create_all(bind=engine)


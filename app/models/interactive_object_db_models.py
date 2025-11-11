"""
SQLAlchemy модель для интерактивных объектов (AR и QR)
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, LargeBinary, Text, Enum
from sqlalchemy.sql import func
from app.database import Base
import enum


class ObjectType(str, enum.Enum):
    """Тип интерактивного объекта"""
    AR = "ar"  # AR объект с распознаванием изображений через ORB
    QR = "qr"  # QR код


class InteractiveObject(Base):
    """Модель интерактивного объекта в БД"""
    __tablename__ = "interactive_objects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)  # HTML контент - основная статья для отображения
    object_type = Column(Enum(ObjectType), nullable=False, index=True)  # 'ar' или 'qr'

    # Для AR объектов - изображение для распознавания
    recognition_image = Column(String(500), nullable=True)  # Путь к изображению для распознавания (AR)

    # Для QR объектов - путь к QR коду и уникальная строка
    qr_code_path = Column(String(500), nullable=True)  # Путь к сгенерированному QR коду
    qr_string = Column(String(100), unique=True, nullable=True, index=True)  # Уникальная строка для QR кода

    # ORB features для распознавания изображений (только для AR)
    orb_keypoints = Column(Text, nullable=True)  # JSON строка с координатами ключевых точек
    orb_descriptors = Column(LargeBinary, nullable=True)  # Бинарные дескрипторы ORB

    # Дополнительное фото для отображения в статье
    photo = Column(String(500), nullable=True)  # Путь к фото объекта для отображения

    # Метаданные
    created_by = Column(String(50), ForeignKey("users.username"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    def __repr__(self):
        return f"<InteractiveObject(id={self.id}, name='{self.name[:30]}...', type='{self.object_type}')>"

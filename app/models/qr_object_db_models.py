"""
SQLAlchemy модели для QR объектов
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class QRObject(Base):
    """Модель QR объекта в БД"""
    __tablename__ = "qr_objects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)  # HTML контент
    photo = Column(String(500), nullable=True)  # Путь к фото объекта
    qr_code_path = Column(String(500), nullable=False)  # Путь к сгенерированному QR коду
    qr_string = Column(String(100), unique=True, nullable=False, index=True)  # Уникальная строка для QR кода
    created_by = Column(String(50), ForeignKey("users.username"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    
    def __repr__(self):
        return f"<QRObject(id={self.id}, name='{self.name[:30]}...')>"


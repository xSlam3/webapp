"""
SQLAlchemy модели для AR тегов
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, LargeBinary, Text
from sqlalchemy.sql import func
from app.database import Base


class ARTag(Base):
    """Модель AR тега в БД"""
    __tablename__ = "ar_tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    description = Column(String(1000), nullable=True)
    tag_image = Column(String(500), nullable=False)  # Путь к изображению тега/QR кода
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=True, index=True)
    created_by = Column(String(50), ForeignKey("users.username"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    # ORB features для распознавания изображений
    orb_keypoints = Column(Text, nullable=True)  # JSON строка с координатами ключевых точек
    orb_descriptors = Column(LargeBinary, nullable=True)  # Бинарные дескрипторы ORB

    def __repr__(self):
        return f"<ARTag(id={self.id}, name='{self.name[:30]}...', material_id={self.material_id})>"


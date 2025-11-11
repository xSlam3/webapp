"""
Миграция для добавления полей ORB признаков в таблицу ar_tags
"""
from sqlalchemy import create_engine, text, LargeBinary, Text, Column
from app.config import DATABASE_URL
from app.models.ar_tag_db_models import ARTag
from app.database import Base, engine
import sys


def add_orb_columns():
    """Добавление колонок для хранения ORB признаков"""
    try:
        with engine.connect() as connection:
            # Проверяем, существуют ли уже колонки
            result = connection.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'ar_tags' AND column_name IN ('orb_keypoints', 'orb_descriptors')"
            ))
            existing_columns = {row[0] for row in result}

            if 'orb_keypoints' not in existing_columns:
                print("Добавление колонки orb_keypoints...")
                connection.execute(text(
                    "ALTER TABLE ar_tags ADD COLUMN orb_keypoints TEXT NULL"
                ))
                connection.commit()
                print("Колонка orb_keypoints добавлена")
            else:
                print("Колонка orb_keypoints уже существует")

            if 'orb_descriptors' not in existing_columns:
                print("Добавление колонки orb_descriptors...")
                connection.execute(text(
                    "ALTER TABLE ar_tags ADD COLUMN orb_descriptors BYTEA NULL"
                ))
                connection.commit()
                print("Колонка orb_descriptors добавлена")
            else:
                print("Колонка orb_descriptors уже существует")

        print("Миграция завершена успешно!")
        return True

    except Exception as e:
        print(f"Ошибка при выполнении миграции: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("Запуск миграции для добавления ORB признаков...")
    success = add_orb_columns()
    sys.exit(0 if success else 1)

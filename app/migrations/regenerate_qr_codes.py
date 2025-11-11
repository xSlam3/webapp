"""
Скрипт для регенерации QR кодов для существующих объектов

После миграции add_qr_string_column.py необходимо запустить этот скрипт,
чтобы обновить QR коды с новыми случайными строками вместо URL.
"""
from pathlib import Path
import sys

# Добавляем корневую директорию в путь
sys.path.append(str(Path(__file__).parent.parent.parent))

from app.database import SessionLocal
from app.models.qr_object_db_models import QRObject
from app.services.qr_object_service import generate_qr_code


def regenerate_all_qr_codes():
    """
    Регенерирует QR коды для всех существующих объектов
    """
    db = SessionLocal()
    try:
        # Получаем все QR объекты
        qr_objects = db.query(QRObject).all()

        if not qr_objects:
            print("ℹ️ QR объекты не найдены в базе данных")
            return

        print(f"🔄 Найдено {len(qr_objects)} QR объектов для регенерации...")

        success_count = 0
        error_count = 0

        for qr_obj in qr_objects:
            try:
                # Генерируем новый QR код с текущей строкой
                qr_code_path = generate_qr_code(qr_obj.qr_string, qr_obj.id)
                qr_obj.qr_code_path = qr_code_path
                db.commit()

                print(f"✓ QR код обновлен для объекта ID {qr_obj.id}: {qr_obj.name}")
                print(f"  QR строка: {qr_obj.qr_string}")
                success_count += 1

            except Exception as e:
                print(f"✗ Ошибка при обновлении QR кода для объекта ID {qr_obj.id}: {e}")
                error_count += 1
                db.rollback()

        print(f"\n📊 Итого:")
        print(f"  ✓ Успешно: {success_count}")
        print(f"  ✗ Ошибок: {error_count}")

        if success_count > 0:
            print("\n✅ QR коды успешно регенерированы!")
            print("ℹ️ Теперь QR коды содержат случайные строки вместо URL")

    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    regenerate_all_qr_codes()

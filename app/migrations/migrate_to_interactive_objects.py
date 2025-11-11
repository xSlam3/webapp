"""
Миграция: объединение AR и QR объектов в единую таблицу interactive_objects

Эта миграция:
1. Создает новую таблицу interactive_objects
2. Мигрирует данные из ar_tags в interactive_objects (с типом 'ar')
3. Мигрирует данные из qr_objects в interactive_objects (с типом 'qr')
4. Опционально сохраняет старые таблицы для отката (не удаляет их)

Запуск: python -m app.migrations.migrate_to_interactive_objects
"""

import sys
from pathlib import Path

# Добавляем корневую директорию в путь для импорта
sys.path.append(str(Path(__file__).parent.parent.parent))

from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, LargeBinary, Text, Enum, MetaData, Table
from sqlalchemy.orm import sessionmaker
from app.database import get_db_url, Base
from app.models.interactive_object_db_models import InteractiveObject, ObjectType
import enum


def migrate():
    """Выполнить миграцию"""
    print("=" * 60)
    print("МИГРАЦИЯ: Объединение AR и QR объектов")
    print("=" * 60)

    # Получаем URL базы данных
    db_url = get_db_url()
    print(f"\n📊 База данных: {db_url}")

    # Создаем движок
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # 1. Создаем новую таблицу interactive_objects
        print("\n1️⃣ Создание таблицы interactive_objects...")
        Base.metadata.create_all(engine, tables=[InteractiveObject.__table__])
        print("✅ Таблица interactive_objects создана")

        # 2. Проверяем существование старых таблиц
        metadata = MetaData()
        metadata.reflect(bind=engine)

        has_ar_tags = 'ar_tags' in metadata.tables
        has_qr_objects = 'qr_objects' in metadata.tables

        print(f"\n2️⃣ Проверка старых таблиц:")
        print(f"   - ar_tags: {'найдена' if has_ar_tags else 'не найдена'}")
        print(f"   - qr_objects: {'найдена' if has_qr_objects else 'не найдена'}")

        migrated_count = 0

        # 3. Мигрируем данные из ar_tags
        if has_ar_tags:
            print("\n3️⃣ Миграция данных из ar_tags...")
            ar_tags_table = metadata.tables['ar_tags']
            ar_tags = session.execute(ar_tags_table.select()).fetchall()

            for ar_tag in ar_tags:
                # Проверяем, не был ли уже мигрирован этот объект
                # (на случай повторного запуска миграции)
                existing = session.query(InteractiveObject).filter(
                    InteractiveObject.name == ar_tag.name,
                    InteractiveObject.object_type == ObjectType.AR
                ).first()

                if existing:
                    print(f"   ⏭️ AR объект '{ar_tag.name}' уже существует, пропускаем...")
                    continue

                # Создаем новый interactive_object из ar_tag
                interactive_obj = InteractiveObject(
                    name=ar_tag.name,
                    description=ar_tag.description,
                    object_type=ObjectType.AR,
                    recognition_image=ar_tag.tag_image,  # tag_image -> recognition_image
                    photo=None,  # В AR тегах не было отдельного фото для отображения
                    qr_code_path=None,
                    qr_string=None,
                    orb_keypoints=ar_tag.orb_keypoints,
                    orb_descriptors=ar_tag.orb_descriptors,
                    created_by=ar_tag.created_by,
                    created_at=ar_tag.created_at,
                    updated_at=ar_tag.updated_at
                )
                session.add(interactive_obj)
                migrated_count += 1
                print(f"   ✅ Мигрирован AR объект: {ar_tag.name}")

            session.commit()
            print(f"✅ Мигрировано {migrated_count} AR объектов")

        # 4. Мигрируем данные из qr_objects
        if has_qr_objects:
            print("\n4️⃣ Миграция данных из qr_objects...")
            qr_objects_table = metadata.tables['qr_objects']
            qr_objects = session.execute(qr_objects_table.select()).fetchall()

            qr_migrated = 0
            for qr_obj in qr_objects:
                # Проверяем, не был ли уже мигрирован
                existing = session.query(InteractiveObject).filter(
                    InteractiveObject.qr_string == qr_obj.qr_string,
                    InteractiveObject.object_type == ObjectType.QR
                ).first()

                if existing:
                    print(f"   ⏭️ QR объект '{qr_obj.name}' уже существует, пропускаем...")
                    continue

                # Создаем новый interactive_object из qr_object
                interactive_obj = InteractiveObject(
                    name=qr_obj.name,
                    description=qr_obj.description,
                    object_type=ObjectType.QR,
                    recognition_image=None,
                    photo=qr_obj.photo,
                    qr_code_path=qr_obj.qr_code_path,
                    qr_string=qr_obj.qr_string,
                    orb_keypoints=None,
                    orb_descriptors=None,
                    created_by=qr_obj.created_by,
                    created_at=qr_obj.created_at,
                    updated_at=qr_obj.updated_at
                )
                session.add(interactive_obj)
                qr_migrated += 1
                print(f"   ✅ Мигрирован QR объект: {qr_obj.name}")

            session.commit()
            migrated_count += qr_migrated
            print(f"✅ Мигрировано {qr_migrated} QR объектов")

        # 5. Итоговая статистика
        print("\n" + "=" * 60)
        print("РЕЗУЛЬТАТЫ МИГРАЦИИ")
        print("=" * 60)

        total_objects = session.query(InteractiveObject).count()
        ar_count = session.query(InteractiveObject).filter(InteractiveObject.object_type == ObjectType.AR).count()
        qr_count = session.query(InteractiveObject).filter(InteractiveObject.object_type == ObjectType.QR).count()

        print(f"\n📊 Всего объектов в interactive_objects: {total_objects}")
        print(f"   - AR объектов: {ar_count}")
        print(f"   - QR объектов: {qr_count}")
        print(f"\n✨ Мигрировано объектов: {migrated_count}")

        # 6. Информация о старых таблицах
        print("\n" + "=" * 60)
        print("ВАЖНО: Старые таблицы НЕ удалены")
        print("=" * 60)
        print("\nСтарые таблицы (ar_tags, qr_objects) сохранены для безопасности.")
        print("После проверки работы новой системы вы можете удалить их вручную.")
        print("\nДля удаления старых таблиц выполните SQL команды:")
        print("  DROP TABLE ar_tags;")
        print("  DROP TABLE qr_objects;")

        print("\n✅ Миграция успешно завершена!")

    except Exception as e:
        print(f"\n❌ Ошибка при миграции: {e}")
        import traceback
        traceback.print_exc()
        session.rollback()
        raise
    finally:
        session.close()


def rollback():
    """Откатить миграцию (удалить таблицу interactive_objects)"""
    print("=" * 60)
    print("ОТКАТ МИГРАЦИИ: Удаление таблицы interactive_objects")
    print("=" * 60)

    response = input("\n⚠️ ВНИМАНИЕ: Это удалит таблицу interactive_objects и все данные в ней!\nПродолжить? (yes/no): ")
    if response.lower() != 'yes':
        print("Откат отменен")
        return

    db_url = get_db_url()
    print(f"\n📊 База данных: {db_url}")

    engine = create_engine(db_url)

    try:
        print("\n🗑️ Удаление таблицы interactive_objects...")
        InteractiveObject.__table__.drop(engine)
        print("✅ Таблица interactive_objects удалена")
        print("\nСтарые таблицы (ar_tags, qr_objects) остались без изменений")

    except Exception as e:
        print(f"\n❌ Ошибка при откате: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Миграция AR и QR объектов')
    parser.add_argument('--rollback', action='store_true', help='Откатить миграцию')
    args = parser.parse_args()

    if args.rollback:
        rollback()
    else:
        migrate()

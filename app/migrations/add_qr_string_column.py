"""
Миграция: Добавление поля qr_string в таблицу qr_objects

Эта миграция добавляет новое поле qr_string для хранения уникальной
случайной строки, которая будет кодироваться в QR код.
"""
import sqlite3
import secrets
import string
from pathlib import Path


def generate_random_string(length=16):
    """Генерирует случайную строку"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def migrate():
    """
    Выполнение миграции
    """
    # Путь к БД (SQLite)
    db_path = Path("app/database.db")

    if not db_path.exists():
        print("⚠️ База данных не найдена. Миграция не требуется для новой БД.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Проверяем, существует ли уже колонка
        cursor.execute("PRAGMA table_info(qr_objects)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'qr_string' in columns:
            print("✓ Колонка qr_string уже существует. Миграция не требуется.")
            return

        print("🔄 Начало миграции: добавление колонки qr_string...")

        # Получаем все существующие записи
        cursor.execute("SELECT id FROM qr_objects")
        existing_ids = [row[0] for row in cursor.fetchall()]

        if not existing_ids:
            # Если нет записей, просто добавляем колонку
            cursor.execute("""
                ALTER TABLE qr_objects
                ADD COLUMN qr_string VARCHAR(100) UNIQUE NOT NULL DEFAULT ''
            """)
            print("✓ Колонка qr_string добавлена (таблица была пустой).")
        else:
            # SQLite не поддерживает изменение колонок напрямую
            # Нужно создать новую таблицу и перенести данные

            print(f"📋 Найдено {len(existing_ids)} существующих QR объектов")

            # Создаем временную таблицу с новой структурой
            cursor.execute("""
                CREATE TABLE qr_objects_new (
                    id INTEGER PRIMARY KEY,
                    name VARCHAR(200) NOT NULL,
                    description TEXT,
                    photo VARCHAR(500),
                    qr_code_path VARCHAR(500) NOT NULL,
                    qr_string VARCHAR(100) UNIQUE NOT NULL,
                    created_by VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP
                )
            """)

            # Генерируем уникальные строки для существующих записей
            qr_strings = set()
            id_to_string = {}

            for obj_id in existing_ids:
                while True:
                    qr_str = generate_random_string()
                    if qr_str not in qr_strings:
                        qr_strings.add(qr_str)
                        id_to_string[obj_id] = qr_str
                        break

            # Копируем данные со случайными строками
            cursor.execute("""
                SELECT id, name, description, photo, qr_code_path,
                       created_by, created_at, updated_at
                FROM qr_objects
            """)

            rows = cursor.fetchall()
            for row in rows:
                obj_id = row[0]
                qr_str = id_to_string[obj_id]
                cursor.execute("""
                    INSERT INTO qr_objects_new
                    (id, name, description, photo, qr_code_path, qr_string,
                     created_by, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (*row, qr_str))

            # Удаляем старую таблицу и переименовываем новую
            cursor.execute("DROP TABLE qr_objects")
            cursor.execute("ALTER TABLE qr_objects_new RENAME TO qr_objects")

            # Создаем индексы
            cursor.execute("CREATE INDEX idx_qr_objects_name ON qr_objects(name)")
            cursor.execute("CREATE UNIQUE INDEX idx_qr_objects_qr_string ON qr_objects(qr_string)")

            print(f"✓ Колонка qr_string добавлена и заполнена для {len(existing_ids)} записей")
            print("⚠️ ВАЖНО: Необходимо перегенерировать QR коды для существующих объектов!")
            print("   Запустите скрипт regenerate_qr_codes.py для обновления QR кодов")

        conn.commit()
        print("✅ Миграция выполнена успешно!")

    except Exception as e:
        conn.rollback()
        print(f"❌ Ошибка при выполнении миграции: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()

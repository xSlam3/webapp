"""
Скрипт инициализации БД с начальными данными
"""
from app.database import init_db, SessionLocal
from app.services.user_service import create_user, get_user_by_username


def init_database():
    """
    Инициализация БД и создание тестовых пользователей
    """
    # Создаем таблицы
    init_db()
    
    db = SessionLocal()
    try:
        # Создаем тестовых пользователей, если их еще нет
        if not get_user_by_username(db, "alice"):
            create_user(db, "alice", "123456", is_admin=False)
            print("✓ Создан пользователь: alice / 123456")
        
        if not get_user_by_username(db, "bob"):
            create_user(db, "bob", "123456", is_admin=True)
            print("✓ Создан пользователь: bob / 123456 (администратор)")
        
        print("✓ База данных инициализирована успешно!")
    except Exception as e:
        print(f"✗ Ошибка при инициализации: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    init_database()


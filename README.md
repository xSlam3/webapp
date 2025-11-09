# Knowledge Base Application

Веб-приложение для управления базой знаний с аутентификацией и админ-панелью.

## Установка

1. Установите зависимости:
```bash
pip install -r requirements.txt
```

2. Создайте файл `.env` в корне проекта (скопируйте из `.env.example`):
```bash
# Database Configuration
DATABASE_URL=sqlite:///./knowledge_base.db

# Security
SECRET_KEY=your-secret-key-here-change-in-production-use-random-string
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Application
DEBUG=True
ENVIRONMENT=development
```

**ВАЖНО**: Измените `SECRET_KEY` на случайную строку в продакшене!

3. Инициализируйте базу данных:
```bash
python -m app.init_db
```

Или просто запустите приложение - БД инициализируется автоматически при старте.

## Запуск

```bash
python main.py
```

Или через uvicorn:
```bash
uvicorn main:app --reload
```

Приложение будет доступно по адресу: http://localhost:8000

## Тестовые аккаунты

После инициализации БД создаются тестовые пользователи:
- **Пользователь**: `alice` / `123456`
- **Администратор**: `bob` / `123456`

## Структура проекта

```
webapp/
├── app/
│   ├── config.py              # Конфигурация из .env
│   ├── database.py            # Настройка SQLAlchemy
│   ├── init_db.py             # Скрипт инициализации БД
│   ├── models/
│   │   ├── material_models.py  # Pydantic модели
│   │   ├── user_models.py     # Pydantic модели
│   │   ├── material_db_models.py  # SQLAlchemy модели
│   │   └── user_db_models.py      # SQLAlchemy модели
│   ├── routers/
│   │   ├── auth_router.py      # Роутер аутентификации
│   │   └── materials_router.py # Роутер материалов
│   ├── services/
│   │   ├── auth.py             # JWT и пароли
│   │   ├── user_service.py     # Сервис пользователей
│   │   ├── material_service.py # Сервис материалов
│   │   └── knowledge_base_utils.py # Утилиты
│   └── templates/              # HTML шаблоны
├── main.py                      # Точка входа
├── requirements.txt             # Зависимости
└── .env                         # Переменные окружения (создать вручную)
```

## База данных

Приложение использует SQLite по умолчанию. Для продакшена рекомендуется использовать PostgreSQL:

```env
DATABASE_URL=postgresql://user:password@localhost/dbname
```

## Безопасность

- Все секреты хранятся в `.env` файле
- Пароли хешируются с помощью bcrypt
- JWT токены для аутентификации
- `.env` файл должен быть в `.gitignore`


-- Скрипт автоматической инициализации базы данных PostgreSQL
-- Этот файл выполняется автоматически при первом запуске контейнера

-- Создание базы данных (если не существует)
-- PostgreSQL автоматически создаёт базу из переменной POSTGRES_DB,
-- но можно добавить дополнительные базы если нужно

-- Проверка подключения
SELECT 'Database initialized successfully!' as status;

-- Можно добавить создание дополнительных расширений
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Пример: создание дополнительной базы для тестов (опционально)
-- SELECT 'CREATE DATABASE webapp_test' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'webapp_test')\gexec

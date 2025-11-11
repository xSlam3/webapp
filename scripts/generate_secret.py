#!/usr/bin/env python3
"""
Генератор безопасного SECRET_KEY для production
"""
import secrets
import string

def generate_secret_key(length=64):
    """
    Генерирует криптографически безопасный секретный ключ

    Args:
        length: Длина ключа (по умолчанию 64 символа)

    Returns:
        str: Секретный ключ
    """
    # Используем URL-safe base64 encoding
    return secrets.token_urlsafe(length)

def generate_password(length=32):
    """
    Генерирует безопасный пароль

    Args:
        length: Длина пароля (по умолчанию 32 символа)

    Returns:
        str: Пароль
    """
    alphabet = string.ascii_letters + string.digits + string.punctuation
    # Удаляем символы, которые могут вызвать проблемы в shell/env
    alphabet = alphabet.replace("'", "").replace('"', "").replace('\\', '').replace('$', '')

    password = ''.join(secrets.choice(alphabet) for _ in range(length))
    return password

if __name__ == "__main__":
    print("=" * 70)
    print("  Генератор секретных ключей для Knowledge Base")
    print("=" * 70)

    print("\n📝 Скопируйте эти значения в ваш .env файл:\n")
    print("-" * 70)

    # Application secrets
    print("# Security Configuration")
    print(f"SECRET_KEY={generate_secret_key()}")
    print()

    # Nginx Proxy Manager passwords
    print("# Nginx Proxy Manager Database")
    print(f"NPM_DB_PASSWORD={generate_password()}")
    print(f"NPM_DB_ROOT_PASSWORD={generate_password()}")
    print()

    # PostgreSQL password
    print("# Application Database (PostgreSQL)")
    print(f"POSTGRES_PASSWORD={generate_password()}")

    print("-" * 70)

    print("\n💡 Советы по безопасности:")
    print("  • Никогда не коммитьте .env файл в Git")
    print("  • Используйте разные ключи для dev и production")
    print("  • Регулярно меняйте пароли (раз в 3-6 месяцев)")
    print("  • Храните бэкапы ключей в безопасном месте (password manager)")
    print()

    print("📌 Следующие шаги:")
    print("  1. Скопируйте значения выше в файл .env")
    print("  2. Запустите: docker compose -f docker-compose.prod.yml up -d")
    print("  3. Откройте Nginx Proxy Manager: http://your-server:81")
    print("  4. Войдите с дефолтными данными:")
    print("     Email: admin@example.com")
    print("     Password: changeme")
    print("  5. СРАЗУ измените пароль администратора!")
    print()

# Архитектура системы

## Схема компонентов

```
┌─────────────────────────────────────────────────────────────────┐
│                         INTERNET                                 │
│                      (Port 80, 443)                              │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│               Nginx Proxy Manager                                │
│                                                                   │
│  • SSL/TLS Termination (Let's Encrypt)                          │
│  • Reverse Proxy                                                 │
│  • Rate Limiting                                                 │
│  • Security Headers                                              │
│  • Admin UI (Port 81 - internal only)                           │
│                                                                   │
│  Networks: nginx_proxy_manager, npm_internal                    │
└───────────────┬──────────────────────┬──────────────────────────┘
                │                       │
                │                       ▼
                │              ┌────────────────┐
                │              │  MySQL (MariaDB) │
                │              │                  │
                │              │  NPM Database   │
                │              │                  │
                │              │  Network:       │
                │              │  npm_internal   │
                │              └────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────────────┐
│              Knowledge Base Web Application                      │
│                                                                   │
│  • FastAPI Backend                                               │
│  • Gunicorn + Uvicorn Workers                                   │
│  • Non-root User                                                 │
│  • Health Checks                                                 │
│  • Port 8000 (internal)                                         │
│                                                                   │
│  Networks: nginx_proxy_manager, kb_network                      │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PostgreSQL Database                           │
│                                                                   │
│  • Application Data                                              │
│  • User Accounts                                                 │
│  • Knowledge Base Content                                        │
│  • Port 5432 (internal only)                                    │
│                                                                   │
│  Network: kb_network                                            │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Backup Service                                 │
│                                                                   │
│  • Automatic Daily Backups (24h interval)                       │
│  • Backup Retention: 7 days                                     │
│  • Compressed SQL dumps (.sql.gz)                               │
│  • Stored in: ./backups/                                        │
│                                                                   │
│  Network: kb_network                                            │
└─────────────────────────────────────────────────────────────────┘
```

## Сети Docker

### 1. nginx_proxy_manager (bridge)
**Назначение:** Связь между Nginx Proxy Manager и веб-приложением

**Участники:**
- nginx-proxy-manager
- web (Knowledge Base App)

**Видимость:** Внутренняя сеть Docker

### 2. npm_internal (bridge, internal)
**Назначение:** Изолированная сеть для Nginx Proxy Manager и его базы данных

**Участники:**
- nginx-proxy-manager
- npm_db (MySQL)

**Видимость:** Полностью изолирована, без доступа извне

### 3. kb_network (bridge)
**Назначение:** Внутренняя сеть приложения и его базы данных

**Участники:**
- web (Knowledge Base App)
- db (PostgreSQL)
- backup (Backup Service)

**Видимость:** Внутренняя сеть Docker

## Volumes (Постоянное хранилище)

### 1. npm_data
- **Тип:** Docker volume
- **Содержимое:** Конфигурация Nginx Proxy Manager
- **Размер:** ~100 MB
- **Бэкап:** Опционально (конфигурация воссоздаваема)

### 2. npm_letsencrypt
- **Тип:** Docker volume
- **Содержимое:** SSL сертификаты Let's Encrypt
- **Размер:** ~50 MB
- **Бэкап:** Важно! (но сертификаты можно перевыпустить)

### 3. npm_mysql_data
- **Тип:** Docker volume
- **Содержимое:** База данных MySQL для NPM
- **Размер:** ~100-500 MB
- **Бэкап:** Опционально (данные воссоздаваемы)

### 4. postgres_data
- **Тип:** Docker volume
- **Содержимое:** База данных PostgreSQL приложения
- **Размер:** Зависит от данных (GB+)
- **Бэкап:** Критично! (автоматический бэкап каждые 24ч)

### 5. uploads_data
- **Тип:** Docker volume
- **Содержимое:** Загруженные пользователями файлы
- **Размер:** Зависит от использования (GB+)
- **Бэкап:** Критично!

### 6. ./backups (bind mount)
- **Тип:** Host directory
- **Содержимое:** SQL бэкапы PostgreSQL
- **Размер:** Зависит от количества бэкапов
- **Бэкап:** Копировать на другой сервер/cloud

### 7. ./logs (bind mount)
- **Тип:** Host directory
- **Содержимое:** Логи приложения
- **Размер:** ~100 MB - 1 GB
- **Бэкап:** Опционально

## Порты

### Открытые наружу (exposed to host):
- **80** → nginx-proxy-manager (HTTP, redirect to HTTPS)
- **443** → nginx-proxy-manager (HTTPS)
- **81** → nginx-proxy-manager (Admin UI, закрыть firewall!)

### Внутренние (internal only):
- **8000** → web (Knowledge Base App)
- **5432** → db (PostgreSQL)
- **3306** → npm_db (MySQL)

## Поток запроса

```
User (HTTPS request)
    ↓
Internet (Port 443)
    ↓
Nginx Proxy Manager
    ↓ [SSL Termination]
    ↓ [Security Headers]
    ↓ [Rate Limiting]
    ↓
Forward to kb_app:8000 (HTTP)
    ↓
Knowledge Base Application
    ↓ [Authentication]
    ↓ [Business Logic]
    ↓
Query PostgreSQL (db:5432)
    ↓
Return Response
    ↓
Nginx Proxy Manager
    ↓ [Add Headers]
    ↓
User (HTTPS response)
```

## Ресурсы по умолчанию

### nginx-proxy-manager
- CPU: Unlimited
- RAM: Unlimited
- Disk: ~200 MB + SSL certs

### npm_db (MySQL)
- CPU: Unlimited
- RAM: ~100-200 MB
- Disk: ~500 MB

### db (PostgreSQL)
- CPU: Unlimited
- RAM: ~200 MB - 2 GB (зависит от данных)
- Disk: Depends on data

### web (Knowledge Base App)
- CPU: Limit 2 cores
- RAM: Limit 2 GB, Reserved 512 MB
- Disk: ~500 MB (image) + uploads

### backup
- CPU: Minimal
- RAM: ~50 MB
- Disk: Depends on backup size

## Безопасность

### Изоляция сети
1. **npm_internal** - полностью изолирована (internal: true)
2. **kb_network** - доступ только между приложением и БД
3. **nginx_proxy_manager** - только NPM ↔ App

### Пользователи в контейнерах
- **nginx-proxy-manager**: root (необходимо для bind портов 80/443)
- **npm_db**: mysql user
- **db**: postgres user
- **web**: appuser (non-root!) ✓
- **backup**: postgres user

### Открытые порты
- Только 80, 443 должны быть доступны из интернета
- Порт 81 (Admin UI) должен быть закрыт firewall
- Все остальные порты - внутренние

## Health Checks

Все сервисы имеют настроенные health checks:

| Service              | Interval | Timeout | Start Period | Retries |
|----------------------|----------|---------|--------------|---------|
| nginx-proxy-manager  | 30s      | 10s     | 60s          | 3       |
| npm_db              | 10s      | 5s      | -            | 5       |
| db                  | 10s      | 5s      | -            | 5       |
| web                 | 30s      | 10s     | 40s          | 3       |

## Зависимости запуска (depends_on)

```
nginx-proxy-manager
    ↓ (depends_on with condition: service_healthy)
npm_db

web
    ↓ (depends_on with condition: service_healthy)
db

backup
    ↓ (depends_on without condition)
db
```

Это гарантирует правильный порядок запуска сервисов.

## Стратегия перезапуска

Все сервисы: `restart: unless-stopped`

- Автоматический перезапуск при падении
- НЕ перезапускается, если остановлен вручную
- Автоматический запуск при старте системы

## Резервное копирование

### Автоматические бэкапы (Backup Service)
- **Частота:** Каждые 24 часа
- **Формат:** Compressed SQL dump (.sql.gz)
- **Хранение:** ./backups/
- **Ротация:** Автоматическое удаление бэкапов старше 7 дней
- **Именование:** backup_YYYYMMDD_HHMMSS.sql.gz

### Что нужно бэкапить вручную (опционально)
1. **./backups/** - копировать на другой сервер/cloud
2. **uploads_data** volume - файлы пользователей
3. **npm_letsencrypt** volume - SSL сертификаты (можно перевыпустить)
4. **.env** файл - ВАЖНО! Секретные ключи

### Что можно не бэкапить
1. npm_data - конфигурация воссоздаваема
2. npm_mysql_data - данные воссоздаваемы
3. Логи - временные данные

## Масштабирование

### Вертикальное масштабирование (больше ресурсов)
Изменить limits в docker-compose.prod.yml:

```yaml
deploy:
  resources:
    limits:
      cpus: '4'        # Увеличить CPU
      memory: 4G       # Увеличить RAM
```

### Горизонтальное масштабирование (больше экземпляров)
1. Запустить несколько экземпляров web:
   ```bash
   docker compose -f docker-compose.prod.yml up -d --scale web=3
   ```

2. Настроить load balancing в Nginx Proxy Manager:
   - Добавить upstream в Advanced config
   - Настроить балансировку между экземплярами

### База данных
Для масштабирования PostgreSQL:
- Master-Slave репликация
- Connection pooling (PgBouncer)
- Отдельный сервер для БД

## Мониторинг

### Встроенный
- Docker health checks
- Container logs
- Resource usage (docker stats)

### Рекомендуемые дополнения
- **Prometheus** + **Grafana** - метрики и дашборды
- **Loki** - агрегация логов
- **Uptime Kuma** - мониторинг доступности
- **Netdata** - real-time monitoring

## Обновление компонентов

### Порядок обновления
1. Создать бэкап
2. Обновить образы:
   ```bash
   docker compose -f docker-compose.prod.yml pull
   ```
3. Остановить сервисы:
   ```bash
   docker compose -f docker-compose.prod.yml down
   ```
4. Запустить с новыми образами:
   ```bash
   docker compose -f docker-compose.prod.yml up -d
   ```
5. Проверить health checks и логи

### Критичность обновлений
- **Nginx Proxy Manager** - регулярно (security patches)
- **PostgreSQL** - осторожно (major version upgrades)
- **MySQL** - регулярно
- **Web App** - по необходимости

## Disaster Recovery

### Полное восстановление системы

1. **Установить Docker и Docker Compose**

2. **Восстановить файлы проекта:**
   ```bash
   git clone <repo>
   cd webapp
   ```

3. **Восстановить .env файл** (из бэкапа!)

4. **Запустить сервисы:**
   ```bash
   docker compose -f docker-compose.prod.yml up -d
   ```

5. **Дождаться готовности баз данных:**
   ```bash
   docker compose -f docker-compose.prod.yml ps
   ```

6. **Восстановить PostgreSQL из бэкапа:**
   ```bash
   docker compose -f docker-compose.prod.yml stop web
   gunzip -c backups/latest.sql.gz | \
     docker compose -f docker-compose.prod.yml exec -T db \
     psql -U kb_user -d knowledge_base
   docker compose -f docker-compose.prod.yml start web
   ```

7. **Восстановить uploads (если есть бэкап):**
   ```bash
   docker volume create uploads_data
   docker run --rm -v uploads_data:/target -v ./uploads_backup:/source alpine sh -c "cp -r /source/* /target/"
   ```

8. **Настроить Nginx Proxy Manager:**
   - Создать Proxy Host
   - Выпустить SSL сертификат

9. **Проверить работу:**
   ```bash
   docker compose -f docker-compose.prod.yml ps
   make health
   ```

**Время восстановления:** ~15-30 минут (зависит от размера данных)

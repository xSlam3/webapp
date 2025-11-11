#!/bin/bash
# Health check скрипт для мониторинга приложения

set -e

echo "================================================"
echo "  Knowledge Base - Health Check"
echo "================================================"

# Цвета для вывода
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Проверка Docker контейнеров
echo -e "\n${YELLOW}Проверка Docker контейнеров...${NC}"
if docker compose -f docker-compose.prod.yml ps | grep -q "Up"; then
    echo -e "${GREEN}✓ Контейнеры запущены${NC}"
    docker compose -f docker-compose.prod.yml ps
else
    echo -e "${RED}✗ Контейнеры не запущены${NC}"
    exit 1
fi

# Проверка health status
echo -e "\n${YELLOW}Проверка health status...${NC}"
WEB_HEALTH=$(docker inspect --format='{{.State.Health.Status}}' kb_app 2>/dev/null || echo "none")
if [ "$WEB_HEALTH" = "healthy" ]; then
    echo -e "${GREEN}✓ Web приложение: healthy${NC}"
else
    echo -e "${RED}✗ Web приложение: $WEB_HEALTH${NC}"
fi

DB_HEALTH=$(docker inspect --format='{{.State.Health.Status}}' kb_postgres 2>/dev/null || echo "none")
if [ "$DB_HEALTH" = "healthy" ]; then
    echo -e "${GREEN}✓ База данных: healthy${NC}"
else
    echo -e "${RED}✗ База данных: $DB_HEALTH${NC}"
fi

# Проверка доступности приложения
echo -e "\n${YELLOW}Проверка доступности приложения...${NC}"
if curl -f -s -o /dev/null http://localhost:8000; then
    echo -e "${GREEN}✓ Приложение отвечает на http://localhost:8000${NC}"
else
    echo -e "${RED}✗ Приложение не отвечает${NC}"
    exit 1
fi

# Проверка использования диска
echo -e "\n${YELLOW}Использование диска Docker volumes...${NC}"
docker system df -v | grep -A 20 "Local Volumes"

# Проверка логов на ошибки (последние 50 строк)
echo -e "\n${YELLOW}Проверка последних логов на ошибки...${NC}"
ERROR_COUNT=$(docker compose -f docker-compose.prod.yml logs --tail=50 web 2>/dev/null | grep -i "error" | wc -l)
if [ "$ERROR_COUNT" -eq 0 ]; then
    echo -e "${GREEN}✓ Ошибок в последних логах не найдено${NC}"
else
    echo -e "${YELLOW}⚠ Найдено ошибок в логах: $ERROR_COUNT${NC}"
    echo "Последние ошибки:"
    docker compose -f docker-compose.prod.yml logs --tail=50 web 2>/dev/null | grep -i "error" | tail -5
fi

# Проверка бэкапов
echo -e "\n${YELLOW}Проверка бэкапов...${NC}"
if [ -d "backups" ]; then
    BACKUP_COUNT=$(ls -1 backups/*.sql.gz 2>/dev/null | wc -l)
    if [ "$BACKUP_COUNT" -gt 0 ]; then
        LATEST_BACKUP=$(ls -t backups/*.sql.gz 2>/dev/null | head -1)
        BACKUP_AGE=$(find "$LATEST_BACKUP" -mtime +1 2>/dev/null)
        echo -e "${GREEN}✓ Найдено бэкапов: $BACKUP_COUNT${NC}"
        echo "  Последний бэкап: $(basename $LATEST_BACKUP)"
        if [ -n "$BACKUP_AGE" ]; then
            echo -e "${YELLOW}  ⚠ Предупреждение: последний бэкап старше 24 часов${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ Бэкапы не найдены${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Директория backups не существует${NC}"
fi

# Использование ресурсов
echo -e "\n${YELLOW}Использование ресурсов контейнерами...${NC}"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" \
    $(docker compose -f docker-compose.prod.yml ps -q)

echo -e "\n${GREEN}================================================${NC}"
echo -e "${GREEN}  Health check завершен${NC}"
echo -e "${GREEN}================================================${NC}"

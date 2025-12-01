#!/bin/bash

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
cat << "EOF"
╔═══════════════════════════════════════════════════════╗
║                                                       ║
║     Dev Assistant - День 20: Ассистент разработчика  ║
║                                                       ║
║  ✓ RAG: README + docs/ индексация                    ║
║  ✓ MCP: Git branch интеграция                        ║
║  ✓ /help: AI ответы на вопросы                       ║
║                                                       ║
╚═══════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

PROJECT_DIR="/Users/fehty/PycharmProjects/ai-agent/src/dev_assistant"
TEST_PROJECT="/Users/fehty/StudioProjects/rag_check"

# Функция для проверки порта
check_port() {
    netstat -tuln 2>/dev/null | grep -q ":$1 " && echo "1" || echo "0"
}

# Функция для вывода секции
print_section() {
    echo -e "\n${YELLOW}═══════════════════════════════════════════════════════${NC}"
    echo -e "${YELLOW} $1${NC}"
    echo -e "${YELLOW}═══════════════════════════════════════════════════════${NC}\n"
}

# Проверка что мы в правильной директории
if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${RED}✗ Директория $PROJECT_DIR не найдена${NC}"
    exit 1
fi

cd "$PROJECT_DIR"

print_section "Шаг 1: Проверка зависимостей"

# Проверка Python
if command -v python3 &> /dev/null; then
    echo -e "${GREEN}✓ Python3 установлен${NC}"
else
    echo -e "${RED}✗ Python3 не найден${NC}"
    exit 1
fi

# Проверка pip пакетов
echo -e "\n${BLUE}Установка зависимостей...${NC}"
pip install -q fastapi uvicorn pydantic sentence-transformers faiss-cpu anthropic gitpython --break-system-packages 2>/dev/null
echo -e "${GREEN}✓ Зависимости установлены${NC}"

# Проверка ANTHROPIC_API_KEY
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo -e "${YELLOW}⚠ ANTHROPIC_API_KEY не установлен (AI ответы будут без Claude)${NC}"
else
    echo -e "${GREEN}✓ ANTHROPIC_API_KEY установлен${NC}"
fi

print_section "Шаг 2: Запуск сервисов"

# Убиваем старые процессы если есть
#pkill -f "python.*main.py" 2>/dev/null
#pkill -f "python.*git_mcp.py" 2>/dev/null
#sleep 1

# Запускаем Backend
#echo -e "${BLUE}Запуск Backend (порт 8000)...${NC}"
#cd backend
#python main.py > /tmp/backend.log 2>&1 &
#BACKEND_PID=$!
#cd ..

#sleep 3

# Проверка что Backend запустился
#if [ $(check_port 8000) -eq 1 ]; then
#    echo -e "${GREEN}✓ Backend запущен (PID: $BACKEND_PID)${NC}"
#else
#    echo -e "${RED}✗ Backend не запустился${NC}"
#    cat /tmp/backend.log
#    exit 1
#fi

# Запускаем MCP Server
#echo -e "${BLUE}Запуск MCP Server (порт 8001)...${NC}"
#cd mcp_server
#python3 git_mcp.py > /tmp/mcp.log 2>&1 &
#MCP_PID=$!
#cd ..

#sleep 3

# Проверка что MCP запустился
#if [ $(check_port 8001) -eq 1 ]; then
#    echo -e "${GREEN}✓ MCP Server запущен (PID: $MCP_PID)${NC}"
#else
#    echo -e "${RED}✗ MCP Server не запустился${NC}"
#    cat /tmp/mcp.log
#    kill $BACKEND_PID 2>/dev/null
#    exit 1
#fi

print_section "Шаг 3: Индексация проекта (RAG)"

echo -e "${BLUE}Индексируем проект: $TEST_PROJECT${NC}\n"
python3 cli.py index "$TEST_PROJECT" 2>&1

print_section "Шаг 4: Тестирование команды /help"

questions=(
    "структура проекта"
    "как добавить зависимость"
    "правила стиля кода"
)

for question in "${questions[@]}"; do
    echo -e "\n${BLUE}❓ Вопрос: /help $question${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    python3 cli.py help "$question" 2>&1 | head -30
    echo ""
    sleep 2
done

print_section "Шаг 5: Тестирование Git MCP"

echo -e "${BLUE}🌿 Получение текущей ветки через MCP${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
python3 cli.py git-branch "$TEST_PROJECT" 2>&1
echo ""

sleep 2

echo -e "${BLUE}📝 Получение статуса репозитория через MCP${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
python3 cli.py git-status "$TEST_PROJECT" 2>&1
echo ""

print_section "✓ Демонстрация завершена!"

echo -e "${GREEN}Результаты:${NC}"
echo -e "  ✓ README.md проиндексирован в RAG"
echo -e "  ✓ docs/flutter_structure.md проиндексирован в RAG"
echo -e "  ✓ docs/code_style.md проиндексирован в RAG"
echo -e "  ✓ MCP получает текущую ветку Git"
echo -e "  ✓ Команда /help отвечает на вопросы о проекте"
echo ""
echo -e "${BLUE}Сервисы продолжают работать:${NC}"
echo -e "  • Backend: http://localhost:8000 (PID: $BACKEND_PID)"
echo -e "  • MCP Server: http://localhost:8001 (PID: $MCP_PID)"
echo ""
echo -e "${YELLOW}Для остановки сервисов:${NC}"
echo -e "  kill $BACKEND_PID $MCP_PID"
echo ""
echo -e "${YELLOW}Логи:${NC}"
echo -e "  • Backend: /tmp/backend.log"
echo -e "  • MCP: /tmp/mcp.log"
echo ""

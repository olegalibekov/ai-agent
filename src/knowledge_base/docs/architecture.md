# Архитектура проекта CloudDocs

## Обзор

CloudDocs - это облачное хранилище файлов с синхронизацией в реальном времени.

## Технологический стек

### Backend
- **FastAPI** - веб-фреймворк
- **PostgreSQL** - основная БД
- **Redis** - кэширование и очереди
- **JWT** - авторизация
- **Docker** - контейнеризация

### Frontend
- **React 18** - UI фреймворк
- **TypeScript** - типизация
- **TailwindCSS** - стилизация
- **React Query** - управление состоянием

### Infrastructure
- **AWS S3** - хранение файлов
- **Kubernetes** - оркестрация
- **GitHub Actions** - CI/CD
- **Prometheus** - мониторинг

## Модули системы

### 1. Auth Module (`/backend/auth`)

Отвечает за авторизацию пользователей:

```python
# /backend/auth/jwt.py
def create_access_token(user_id: str) -> str:
    """Создает JWT токен для пользователя"""
    payload = {
        "user_id": user_id,
        "exp": datetime.utcnow() + timedelta(minutes=15)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def verify_token(token: str) -> dict:
    """Проверяет валидность токена"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise UnauthorizedError("Token expired")
```

**Известные проблемы:**
- TASK-101: Баг с истечением токенов после смены пароля
- Нужно инвалидировать старые токены в Redis

### 2. Storage Module (`/backend/storage`)

Управление файлами:

```python
# /backend/storage/uploader.py
class FileUploader:
    def __init__(self, s3_client):
        self.s3 = s3_client
    
    async def upload_file(self, file: UploadFile, user_id: str):
        """Загружает файл в S3"""
        # Проверка размера файла по плану
        user_plan = await get_user_plan(user_id)
        max_size = PLAN_LIMITS[user_plan]["max_file_size"]
        
        if file.size > max_size:
            raise FileSizeExceededError(f"Max size: {max_size}")
        
        # Загрузка в S3
        key = f"{user_id}/{file.filename}"
        await self.s3.upload(key, file)
```

### 3. Sync Module (`/backend/sync`)

Синхронизация между устройствами:

```python
# /backend/sync/websocket.py
class SyncManager:
    async def notify_clients(self, user_id: str, event: dict):
        """Отправляет обновления всем клиентам пользователя"""
        clients = await self.redis.get(f"user:{user_id}:clients")
        
        for client_id in clients:
            await self.send_event(client_id, event)
```

**Известные проблемы:**
- Иногда файлы не синхронизируются (WebSocket connection drops)
- Нужно добавить retry механизм

## API Endpoints

### Authentication
```
POST   /api/auth/register       # Регистрация
POST   /api/auth/login          # Вход
POST   /api/auth/refresh        # Обновление токена
POST   /api/auth/logout         # Выход
```

### Files
```
GET    /api/files               # Список файлов
POST   /api/files/upload        # Загрузка
GET    /api/files/{id}          # Скачать файл
DELETE /api/files/{id}          # Удалить
PUT    /api/files/{id}/share    # Поделиться
```

### Sync
```
WS     /api/sync/ws             # WebSocket для синхронизации
GET    /api/sync/status         # Статус синхронизации
```

## База данных

### Схема Users
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    plan VARCHAR(50) DEFAULT 'free',
    storage_used BIGINT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Схема Files
```sql
CREATE TABLE files (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    filename VARCHAR(255) NOT NULL,
    size BIGINT NOT NULL,
    s3_key VARCHAR(500) NOT NULL,
    uploaded_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_user_id (user_id)
);
```

## Развертывание

### Локальная разработка
```bash
docker-compose up -d
python -m uvicorn main:app --reload
```

### Production
```bash
kubectl apply -f k8s/
```

## Мониторинг

- **Метрики**: Prometheus собирает метрики каждые 15 секунд
- **Алерты**: PagerDuty для критических проблем
- **Логи**: CloudWatch Logs

## Security

- Rate limiting: 100 запросов/минуту на IP
- CORS: только с разрешенных доменов
- Шифрование: TLS 1.3 для всех соединений
- Secrets: AWS Secrets Manager

## Performance

- Кэширование: Redis для часто запрашиваемых данных
- CDN: CloudFront для статических файлов
- Database: Read replicas для масштабирования чтения

## Known Issues

1. **TASK-101**: Баг с JWT токенами после смены пароля
2. **TASK-103**: Уязвимости в зависимостях (CVE-2024-12345)
3. **TASK-108**: Недостаточное покрытие тестами (75% вместо 80%)

## Future Plans

- Добавить поддержку версионирования файлов
- Реализовать collaborative editing
- Интеграция с Google Drive

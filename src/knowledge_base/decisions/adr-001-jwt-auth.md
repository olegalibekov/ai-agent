# ADR-001: Выбор JWT для авторизации

## Статус
Принято (2025-10-15)

## Контекст
Нам нужна система авторизации для CloudDocs API. Рассматривали несколько вариантов:
- Session-based auth (cookies)
- JWT tokens
- OAuth 2.0

## Решение
Выбрали JWT (JSON Web Tokens) для авторизации.

## Обоснование

### Плюсы JWT:
1. **Stateless** - не нужно хранить сессии в БД
2. **Масштабируемость** - легко работает с multiple серверами
3. **Mobile-friendly** - просто использовать в мобильных приложениях
4. **Payload** - можем хранить данные пользователя в токене

### Минусы JWT:
1. **Нельзя отозвать** - токен валиден до истечения
2. **Размер** - больше чем session ID
3. **Security** - нужно хранить secret надежно

## Реализация

- Access token: 15 минут
- Refresh token: 30 дней
- Алгоритм: HS256
- Storage: HttpOnly cookies для web, localStorage для mobile

## Решение проблемы отзыва

Добавили Redis blacklist для отзыва токенов:
- При logout/password change добавляем токен в blacklist
- При проверке токена проверяем blacklist
- TTL blacklist = время жизни refresh token

## Последствия

✅ Упростилась архитектура (не нужна session storage)
✅ Улучшилась производительность (меньше DB queries)
⚠️ Усложнилась логика отзыва токенов (нужен Redis)
⚠️ Нужен мониторинг утечек secret key

## Альтернативы

Если JWT не подойдет, можем перейти на:
- OAuth 2.0 с authorization server
- Session-based auth с Redis session store

## Related
- TASK-101: Баг с invalidation токенов
- TASK-107: Нужен rate limiting для /auth endpoints

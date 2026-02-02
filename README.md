# Система Аутентификации и Авторизации

## Описание проекта

Это backend-приложение реализует собственную систему аутентификации и авторизации с использованием Django REST Framework. Проект демонстрирует глубокое понимание механизмов безопасности, управления доступом и работы с пользовательскими сессиями.

## Технологический стек

- **Backend**: Django 4.2.9
- **API**: Django REST Framework 3.14.0
- **Аутентификация**: JWT токены (djangorestframework-simplejwt)
- **База данных**: SQLite (для разработки) / PostgreSQL (для продакшена)
- **Документация API**: drf-spectacular (Swagger/OpenAPI)

## Архитектура системы разграничения прав доступа

### 1. Основные понятия

#### 1.1 Аутентификация (Authentication)
**Аутентификация** - процесс проверки подлинности пользователя, определение "кто ты?".

В нашей системе используется:
- **JWT (JSON Web Tokens)** для статeless аутентификации
- Access Token (короткоживущий, 15 минут) для доступа к API
- Refresh Token (долгоживущий, 7 дней) для обновления access token

#### 1.2 Авторизация (Authorization)
**Авторизация** - процесс проверки прав доступа, определение "что тебе разрешено делать?".

В нашей системе реализована гибридная модель:
- **RBAC (Role-Based Access Control)** - доступ на основе ролей
- **ABAC (Attribute-Based Access Control)** - доступ на основе атрибутов ресурсов
- **Permission-Based** - прямое назначение разрешений

### 2. Структура базы данных

#### 2.1 Таблица `users` (Пользователи)

```
User
├── id (PK)
├── email (unique)
├── password (hashed)
├── first_name
├── middle_name
├── last_name
├── is_active (для мягкого удаления)
├── is_staff
├── is_superuser
├── created_at
└── updated_at
```

**Особенности:**
- `is_active=False` - пользователь "удалён", не может войти в систему
- Пароли хранятся в хешированном виде (PBKDF2 + SHA256)
- Email используется как уникальный идентификатор для входа

#### 2.2 Таблица `roles` (Роли)

```
Role
├── id (PK)
├── name (unique) - например: "admin", "manager", "user", "guest"
├── description
├── created_at
└── updated_at
```

**Предустановленные роли:**
- `admin` - администратор системы, полный доступ
- `manager` - менеджер, управление ресурсами
- `editor` - редактор, создание и изменение контента
- `viewer` - наблюдатель, только чтение
- `guest` - гость, ограниченный доступ

#### 2.3 Таблица `permissions` (Разрешения)

```
Permission
├── id (PK)
├── code (unique) - например: "document.create", "user.delete"
├── name
├── description
├── resource_type - тип ресурса (document, user, project, etc.)
├── action - действие (create, read, update, delete, execute)
├── created_at
└── updated_at
```

**Формат разрешений**: `{resource_type}.{action}`

Примеры:
- `document.create` - создание документов
- `document.read` - чтение документов
- `document.update` - изменение документов
- `document.delete` - удаление документов
- `user.manage` - управление пользователями
- `project.execute` - выполнение проектов

#### 2.4 Таблица `user_roles` (Связь пользователей и ролей)

```
UserRole (Many-to-Many)
├── id (PK)
├── user_id (FK -> User)
├── role_id (FK -> Role)
├── assigned_at
└── assigned_by (FK -> User)
```

**Особенности:**
- Один пользователь может иметь несколько ролей
- Права аккумулируются (объединение всех прав от всех ролей)

#### 2.5 Таблица `role_permissions` (Связь ролей и разрешений)

```
RolePermission (Many-to-Many)
├── id (PK)
├── role_id (FK -> Role)
├── permission_id (FK -> Permission)
├── granted_at
└── granted_by (FK -> User)
```

**Особенности:**
- Роль может иметь множество разрешений
- При изменении разрешений роли меняются права всех пользователей с этой ролью

#### 2.6 Таблица `user_permissions` (Прямые разрешения пользователей)

```
UserPermission (Many-to-Many)
├── id (PK)
├── user_id (FK -> User)
├── permission_id (FK -> Permission)
├── is_granted (True/False) - разрешить или запретить
├── granted_at
└── granted_by (FK -> User)
```

**Особенности:**
- Позволяет переопределить права, полученные через роли
- `is_granted=False` - явный запрет (DENY), приоритет над разрешениями
- `is_granted=True` - явное разрешение (ALLOW)

#### 2.7 Таблица `resource_permissions` (Разрешения на уровне ресурсов)

```
ResourcePermission
├── id (PK)
├── user_id (FK -> User)
├── resource_type (string) - "document", "project", "task"
├── resource_id (string) - ID конкретного ресурса
├── permission_id (FK -> Permission)
├── is_granted (True/False)
├── granted_at
└── granted_by (FK -> User)
```

**Особенности:**
- Детальный контроль доступа к конкретным объектам
- Например: пользователь может редактировать документ #5, но не #10
- Приоритет: Resource-level > User-level > Role-level

### 3. Логика проверки прав доступа

#### Алгоритм проверки (Priority Order):

```python
def check_permission(user, resource_type, action, resource_id=None):
    """
    Проверка наличия разрешения у пользователя
    
    Приоритет проверок:
    1. Суперпользователь - всегда True
    2. Неактивный пользователь - всегда False
    3. Resource-level DENY - всегда False
    4. Resource-level ALLOW - True
    5. User-level DENY - False
    6. User-level ALLOW - True
    7. Role-level - проверка через роли
    8. Default - False
    """
    
    # 1. Суперпользователь
    if user.is_superuser:
        return True
    
    # 2. Неактивный пользователь
    if not user.is_active:
        return False
    
    permission_code = f"{resource_type}.{action}"
    
    # 3-4. Resource-level разрешения (если указан конкретный ресурс)
    if resource_id:
        resource_perm = check_resource_permission(user, permission_code, resource_id)
        if resource_perm is not None:  # Явно указано
            return resource_perm
    
    # 5-6. User-level разрешения (прямые)
    user_perm = check_user_permission(user, permission_code)
    if user_perm is not None:  # Явно указано
        return user_perm
    
    # 7. Role-level разрешения
    if check_role_permission(user, permission_code):
        return True
    
    # 8. По умолчанию - запретить
    return False
```

#### Примеры работы системы:

**Пример 1: Администратор**
```
User: admin@company.com
Roles: [admin]
Role "admin" permissions: [*.* (все разрешения)]

Запрос: document.delete на document_id=123
Результат: ✅ Разрешено (через роль admin)
```

**Пример 2: Менеджер с ограничением**
```
User: manager@company.com
Roles: [manager]
Role "manager" permissions: [document.read, document.update, project.read]
User direct permissions: [document.delete: DENY]

Запрос: document.delete на document_id=123
Результат: ❌ Запрещено (явный DENY на уровне пользователя)
```

**Пример 3: Редактор с дополнительными правами**
```
User: editor@company.com
Roles: [editor]
Role "editor" permissions: [document.create, document.update]
User direct permissions: [document.delete: ALLOW для document_id=555]

Запрос: document.delete на document_id=555
Результат: ✅ Разрешено (resource-level ALLOW)

Запрос: document.delete на document_id=777
Результат: ❌ Запрещено (нет прав)
```

**Пример 4: Наблюдатель**
```
User: viewer@company.com
Roles: [viewer]
Role "viewer" permissions: [document.read, project.read]

Запрос: document.read
Результат: ✅ Разрешено (через роль viewer)

Запрос: document.update
Результат: ❌ Запрещено (нет прав)
```

### 4. HTTP Status Codes

- **200 OK** - успешный запрос
- **201 Created** - ресурс создан
- **204 No Content** - успешное удаление
- **400 Bad Request** - некорректные данные
- **401 Unauthorized** - пользователь не аутентифицирован (нет токена или токен невалиден)
- **403 Forbidden** - пользователь аутентифицирован, но не имеет прав доступа
- **404 Not Found** - ресурс не найден

### 5. API Endpoints

#### 5.1 Аутентификация и управление пользователями

```
POST   /api/auth/register/          - Регистрация нового пользователя
POST   /api/auth/login/             - Вход в систему (получение JWT токенов)
POST   /api/auth/logout/            - Выход из системы
POST   /api/auth/refresh/           - Обновление access token
GET    /api/auth/profile/           - Просмотр своего профиля
PUT    /api/auth/profile/           - Обновление профиля
DELETE /api/auth/profile/           - Удаление аккаунта (мягкое удаление)
```

#### 5.2 Управление правами доступа (только для администраторов)

```
# Роли
GET    /api/permissions/roles/                     - Список ролей
POST   /api/permissions/roles/                     - Создание роли
GET    /api/permissions/roles/{id}/                - Детали роли
PUT    /api/permissions/roles/{id}/                - Обновление роли
DELETE /api/permissions/roles/{id}/                - Удаление роли

# Разрешения
GET    /api/permissions/permissions/               - Список разрешений
POST   /api/permissions/permissions/               - Создание разрешения
GET    /api/permissions/permissions/{id}/          - Детали разрешения
PUT    /api/permissions/permissions/{id}/          - Обновление разрешения
DELETE /api/permissions/permissions/{id}/          - Удаление разрешения

# Назначение ролей пользователям
POST   /api/permissions/users/{id}/assign-role/    - Назначить роль пользователю
POST   /api/permissions/users/{id}/revoke-role/    - Отозвать роль у пользователя

# Прямые разрешения пользователям
POST   /api/permissions/users/{id}/grant-permission/   - Дать разрешение
POST   /api/permissions/users/{id}/revoke-permission/  - Отозвать разрешение

# Связывание разрешений с ролями
POST   /api/permissions/roles/{id}/add-permission/     - Добавить разрешение к роли
POST   /api/permissions/roles/{id}/remove-permission/  - Удалить разрешение из роли
```

#### 5.3 Mock бизнес-объекты (демонстрация работы системы)

```
GET    /api/business/documents/         - Список документов (требует: document.read)
POST   /api/business/documents/         - Создание документа (требует: document.create)
GET    /api/business/documents/{id}/    - Просмотр документа (требует: document.read)
PUT    /api/business/documents/{id}/    - Изменение документа (требует: document.update)
DELETE /api/business/documents/{id}/    - Удаление документа (требует: document.delete)

GET    /api/business/projects/          - Список проектов (требует: project.read)
POST   /api/business/projects/          - Создание проекта (требует: project.create)
GET    /api/business/projects/{id}/     - Просмотр проекта (требует: project.read)
PUT    /api/business/projects/{id}/     - Изменение проекта (требует: project.update)
DELETE /api/business/projects/{id}/     - Удаление проекта (требует: project.delete)
```

### 6. Тестовые данные

При первом запуске система создаст:

#### Пользователи:
1. **Суперадмин**: `admin@test.com` / `admin123` - полный доступ
2. **Менеджер**: `manager@test.com` / `manager123` - управление документами и проектами
3. **Редактор**: `editor@test.com` / `editor123` - создание и редактирование
4. **Наблюдатель**: `viewer@test.com` / `viewer123` - только чтение

#### Роли и их разрешения:
- **admin**: все разрешения
- **manager**: document.*, project.read, project.update
- **editor**: document.create, document.update, project.create
- **viewer**: document.read, project.read

## Установка и запуск

### 1. Клонирование и установка зависимостей

```bash
# Создать виртуальное окружение
python -m venv venv

# Активировать виртуальное окружение
# Windows:
.\venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Установить зависимости
pip install -r requirements.txt
```

### 2. Настройка базы данных

```bash
# Создать миграции
python manage.py makemigrations

# Применить миграции
python manage.py migrate

# Загрузить тестовые данные
python manage.py loaddata initial_data.json
```

### 3. Запуск сервера

```bash
python manage.py runserver
```

API будет доступен по адресу: `http://127.0.0.1:8000/`

### 4. Документация API

После запуска сервера документация доступна:
- Swagger UI: `http://127.0.0.1:8000/api/docs/`
- ReDoc: `http://127.0.0.1:8000/api/redoc/`

## Примеры использования API

### 1. Регистрация пользователя

```bash
curl -X POST http://127.0.0.1:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@test.com",
    "password": "securepass123",
    "password_confirm": "securepass123",
    "first_name": "Иван",
    "last_name": "Иванов",
    "middle_name": "Иванович"
  }'
```

### 2. Вход в систему (Login)

```bash
curl -X POST http://127.0.0.1:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@test.com",
    "password": "admin123"
  }'
```

Ответ:
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": 1,
    "email": "admin@test.com",
    "first_name": "Администратор"
  }
}
```

### 3. Получение профиля (с использованием токена)

```bash
curl -X GET http://127.0.0.1:8000/api/auth/profile/ \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..."
```

### 4. Создание документа (требуется разрешение)

```bash
curl -X POST http://127.0.0.1:8000/api/business/documents/ \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..." \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Новый документ",
    "content": "Содержимое документа"
  }'
```

### 5. Назначение роли пользователю (только admin)

```bash
curl -X POST http://127.0.0.1:8000/api/permissions/users/5/assign-role/ \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..." \
  -H "Content-Type: application/json" \
  -d '{
    "role_id": 2
  }'
```

## Ключевые особенности реализации

### 1. JWT Токены

- **Access Token**: живёт 15 минут, используется для доступа к API
- **Refresh Token**: живёт 7 дней, используется для получения нового access token
- Токены содержат: user_id, email, roles
- При logout refresh token добавляется в blacklist

### 2. Безопасность

- Пароли хешируются с использованием PBKDF2-SHA256
- Минимальная длина пароля: 8 символов
- Защита от CSRF атак
- Rate limiting для предотвращения брутфорса
- SQL Injection защита (через ORM Django)

### 3. Мягкое удаление

При удалении аккаунта:
1. `is_active` устанавливается в `False`
2. Происходит автоматический logout
3. Данные остаются в базе для аудита
4. Пользователь не может войти снова

### 4. Производительность

- Индексы на часто используемых полях (email, code)
- Select_related/Prefetch_related для оптимизации запросов
- Кеширование проверок прав (опционально)

## Заключение

Данная система демонстрирует:
- Глубокое понимание разницы между аутентификацией и авторизацией
- Знание работы JWT токенов и сессий
- Понимание принципов безопасности веб-приложений
- Навыки проектирования гибких систем управления доступом
- Умение работать с DRF и PostgreSQL/SQLite

Система легко масштабируется и может быть адаптирована под любые бизнес-требования.

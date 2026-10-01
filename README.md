# JuniorJobs — доска вакансий для начинающих разработчиков

REST API сервиса, где компании публикуют вакансии для джунов и стажёров, а кандидаты ищут их
по навыкам, городу, формату работы, опыту и зарплате, сохраняют в избранное, подписываются
на интересные компании и задают работодателю вопросы прямо под вакансией.

**Стек:** Python 3.12 · Django 5/6 · Django REST Framework · PyJWT · PostgreSQL (SQLite для
локальной разработки) · drf-spectacular (OpenAPI) · pytest-django · Docker · GitHub Actions.

## Предметная область

- **Компании и кандидаты.** При регистрации можно указать `isCompany` и `companyName`;
  публиковать и менять вакансии может только аккаунт компании и только свои.
- **Вакансия:** заголовок, краткое и полное описание, вилка зарплаты (`salaryFrom` ≤ `salaryTo`,
  проверяется и сериализатором, и `CheckConstraint` в БД), город, удалёнка, опыт
  (`noExperience` / `between1And3` / `between3And6` / `moreThan6` — те же значения, что в фильтре hh.ru),
  навыки.
- **Фильтры списка:** `skill`, `company`, `saved`, `city`, `remote`, `experience`, `salaryMin`, `limit`, `offset`.

## API

Все маршруты — под `/api`. Документация OpenAPI: `/api/docs` (Swagger UI), схема — `/api/schema`.
Авторизация: заголовок `Authorization: Bearer <token>`.

| Метод | Путь | Доступ | Назначение |
|---|---|---|---|
| POST | `/users` | все | Регистрация кандидата или компании |
| POST | `/users/login` | все | Вход, выдаёт JWT |
| GET / PUT | `/user` | авторизованные | Текущий пользователь / обновление профиля |
| GET | `/profiles/{username}` | все | Профиль кандидата или компании |
| POST / DELETE | `/profiles/{username}/follow` | авторизованные | Подписаться / отписаться |
| GET | `/vacancies` | все | Список с фильтрами и пагинацией |
| GET | `/vacancies/feed` | авторизованные | Вакансии компаний из подписок |
| POST | `/vacancies` | компании | Опубликовать вакансию |
| GET / PUT / DELETE | `/vacancies/{slug}` | все / владелец / владелец | Получить / изменить / удалить |
| POST / DELETE | `/vacancies/{slug}/save` | авторизованные | Сохранить в избранное / убрать |
| GET / POST | `/vacancies/{slug}/questions` | все / авторизованные | Вопросы к работодателю |
| DELETE | `/vacancies/{slug}/questions/{id}` | автор вопроса или владелец вакансии | Удалить вопрос |
| GET | `/skills` | все | Все навыки |

## Быстрый старт

### Docker

```bash
docker compose up --build                            # API: http://localhost:8001/api/docs
docker compose exec app python manage.py seed_demo   # демо: 3 компании, 2 кандидата, 8 вакансий
```

### Локально

```bash
uv sync --group dev
uv run python manage.py migrate        # без DATABASE_URL используется SQLite
uv run python manage.py seed_demo
uv run python manage.py runserver
```

Демо-аккаунты (пароль `demo-password`): компании `techstart@juniorjobs.dev`, `datalab@juniorjobs.dev`,
`cloudplus@juniorjobs.dev`; кандидаты `maria_junior@juniorjobs.dev`, `oleg_qa@juniorjobs.dev`.
Компании и вакансии вымышленные.

## Тесты

```bash
uv run pytest                                          # SQLite
DATABASE_URL=postgres://postgres:postgres@localhost:5432/jobboard uv run pytest   # PostgreSQL
uv run ruff check . && uv run ruff format --check .
```

Регистронезависимый поиск по городу для кириллицы полноценно работает в PostgreSQL: `LIKE` в SQLite
сворачивает регистр только для ASCII. Соответствующий тест запускается только на PostgreSQL.

## Структура

```
jobboard/
├── settings.py, urls.py           # настройки из переменных окружения, маршруты, OpenAPI
└── apps/
    ├── core/                      # TimestampedModel, JSON-рендерер, обработчик ошибок, пагинация
    ├── authentication/            # User, JWT-бэкенд, регистрация/вход/профиль пользователя
    ├── profiles/                  # профили кандидатов и компаний, подписки
    └── vacancies/                 # вакансии, навыки, вопросы, фильтры, права, сид-команда
tests/                             # pytest-django: авторизация, профили, вакансии, вопросы
```

## Идеи для развития

- Отклик на вакансию с сопроводительным письмом и статусами «на рассмотрении / приглашение / отказ».
- Полнотекстовый поиск по описанию (`SearchVector` + GIN-индекс с русской конфигурацией).
- Импорт вакансий компании из API hh.ru по её employer_id.
- Уведомления в Telegram о новых вакансиях по сохранённому фильтру.

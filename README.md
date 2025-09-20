# Sticker Floor Watcher

Приватный бот для наблюдения за коллекциями стикеров на Harbor, MRKT, Palace и Pixel Market. Отправляет мгновенные алерты о падении пола, редких листингах, тонком полу и формирует 15-минутные отчёты и дайджесты (10:00 и 20:00 Europe/Amsterdam).

## Основные возможности

- Асинхронные адаптеры для Harbor (REST API) и Mini App рынков (через валидированное initData).
- Хранение истории floor/depth в PostgreSQL, кэш и антиспам на Redis.
- Aiogram 3 + FastAPI вебхук, отдельный воркер с APScheduler для мониторинга коллекций и отправки дайджестов.
- Команды бота: `/watch`, `/unwatch`, `/list`, `/digest`, `/mute`, `/unmute`, `/export`.

## Структура

```
sticker_watcher/
  adapters/         # Harbor + Telegram Mini App интеграции
  bot/              # Aiogram bot, обработчики и middleware
  services/         # Сcheduler, метрики, уведомления, digest менеджер
  models/           # SQLAlchemy модели БД
  main.py           # FastAPI приложение (вебхук)
  worker.py         # Фоновый воркер с APScheduler
```

## Быстрый старт (Docker Compose)

```bash
cp .env.example .env
# заполните переменные (токен бота, initData, deeplink, whitelist)
docker compose up --build
```

Сервис `api` поднимает FastAPI + вебхук, `worker` запускает мониторинг. Postgres и Redis автоматически стартуют.

## Подготовка БД

После настройки `.env` выполните миграцию схемы:

```bash
docker compose run --rm api python scripts/create_tables.py
```

Добавьте записи рынков/коллекций (market code: `harbor`, `mrkt`, `palace`, `pixel`) и meta с конфигурацией API или Mini App.

## Тестирование

- `ruff` для статического анализа.
- (опционально) `pytest` для unit-тестов.

## Лицензия

Проект приватный, распространяется только внутри команды.

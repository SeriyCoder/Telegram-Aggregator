# Telegram Knowledge Base

Локальная персональная база знаний для публикаций из выбранных Telegram-каналов.
Приложение на этом этапе только создаёт локальную базу данных; HTTP-сервер,
Telegram-подключение и аутентификация пока не запускаются.

## Требования

- Python 3.12 или новее
- Windows PowerShell 5.1 или новее

## Установка

Из корневого каталога проекта выполните:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Файл `.env.example` перечисляет стандартные ограничения. Приложение читает
настройки из окружения процесса и не загружает `.env` автоматически.

| Переменная | По умолчанию | Допустимое значение |
| --- | --- | --- |
| `TKB_DATA_DIR` | Системный каталог пользовательских данных | Не пустой абсолютный путь вне каталога проекта |
| `TKB_COLLECTION_LIMIT` | `500` | Целое число от 1 до 500 |
| `TKB_PAGE_SIZE` | `50` | Целое число от 1 до 100 |

Данные и будущие файлы авторизации Telegram хранятся вне каталога проекта.
Не задавайте `TKB_DATA_DIR` каталогом проекта или его подпапкой.

## Запуск

```powershell
.\.venv\Scripts\python.exe -m telegram_knowledge_base
```

При первом запуске создаётся SQLite-база с начальной схемой в пользовательском
каталоге данных. Повторный запуск сохраняет существующие данные.

## Проверки

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m mypy src
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
```

Все тесты работают офлайн и не требуют Telegram-сессии.

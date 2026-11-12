# Telegram Knowledge Base

Локальная персональная база знаний для публикаций из выбранных Telegram-каналов.
Приложение создаёт локальную базу и поддерживает работу с уже добавленными
локально источниками. Реальный вход и доступ к Telegram намеренно заблокированы
до выяснения применимости требований платформы к этому сценарию. HTTP-сервер
ещё не реализован.

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

Данные и защищённая сессия Telegram должны храниться вне каталога проекта.
`TKB_DATA_DIR` обязан быть локальным каталогом, не сетевой папкой и не папкой
OneDrive, Dropbox или Google Drive. SQLite не шифрует сохранённые публикации.

## Запуск

```powershell
.\.venv\Scripts\python.exe -m telegram_knowledge_base
```

При первом запуске создаётся SQLite-база с начальной схемой в пользовательском
каталоге данных. Повторный запуск сохраняет существующие данные.

Доступны локальные команды:

```powershell
.\.venv\Scripts\python.exe -m telegram_knowledge_base status
.\.venv\Scripts\python.exe -m telegram_knowledge_base source list
.\.venv\Scripts\python.exe -m telegram_knowledge_base source enable <ID>
.\.venv\Scripts\python.exe -m telegram_knowledge_base source disable <ID>
```

Команды `login`, `source add` и `sync` завершаются безопасным сообщением, пока
не снята блокировка реального доступа. Даже заданные `TKB_API_ID` и
`TKB_API_HASH` не включают подключение. Закрытые каналы не поддерживаются;
собранная версия поста впоследствии автоматически не обновляется и не удаляется.

## Проверки

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m mypy src
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
```

Все тесты работают офлайн и не требуют Telegram-сессии.

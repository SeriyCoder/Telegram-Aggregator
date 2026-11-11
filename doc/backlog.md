# Backlog

IDs are `<EPIC>-<NN>`. Status: `[ ]` open, `[x]` done.
Only `/4-close` ticks a box.
Specification: [doc/spec/telegram-knowledge-base.md](spec/telegram-knowledge-base.md).

## CONTOUR — Process

- [ ] CONTOUR-01 Verify at the next `/5-audit` the contour installed directly on
  2026-11-11

## MVP — Локальная база знаний

- [ ] MVP-01 Создать Python-инструментарий и безопасную локальную конфигурацию
  (первый пункт создает окружение, структуру приложения и тестовые команды)
- [ ] MVP-02 Реализовать управляемый и идемпотентный сбор публикаций Telegram
- [ ] MVP-03 Добавить правила отбора, теги, закладки и полнотекстовый поиск
- [ ] MVP-04 Создать адаптивную веб-ленту, LAN-аутентификацию и локальную
  инструкцию по резервированию и восстановлению

## FUTURE — После MVP

- [ ] FUTURE-01 Оценить альтернативные способы подключения (Tailscale,
  Cloudflare Tunnel или другие) отдельным решением; не включать их в MVP

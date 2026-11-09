# Архитектура WEB-Constructor

## Слои
1. Application Shell — окно, навигация, общие панели и жизненный цикл.
2. Core — конфигурация, события, команды, хранение, версии данных и контракты.
3. Feature Modules — изолированные функции через реестр.
4. Project Model — независимое от UI представление сайта.
5. Editor Adapters — связь визуальных движков с Project Model.
6. Export Engine — генерация чистого сайта.
7. Documentation — FAQ и технические документы.

## Ограничения
- Project Model не зависит от GrapesJS или DOM.
- Export Engine не импортирует UI или pywebview.
- UI не меняет файлы проекта в обход сервисов хранения.
- Модули используют публичные интерфейсы Core.
- Формат проекта имеет schema_version и последовательные миграции.
- Экспорт содержит только используемые ресурсы и работает независимо от приложения.
- Идентификаторы проектов — UUID; они не используются как произвольные пути файловой системы.
- Запись project.json выполняется через временный файл и атомарную замену.

## Хранение проектов
- Windows: %LOCALAPPDATA%/WEB-Constructor/projects.
- Linux/macOS fallback: $XDG_DATA_HOME/WEB-Constructor/projects или ~/.local/share/WEB-Constructor/projects.
- Один проект — одна папка UUID.
- Внутри: project.json, assets/, exports/.
- project.json — единственный источник истины для метаданных сайта и дерева страниц.

## Project Model v1
- schema_version.
- project: id, name, created_at, updated_at.
- site: title, description, language.
- pages: id, title, slug, is_home, content.nodes.
- Каждый узел content.nodes имеет id, type, props и children; вложенность описывает структуру документа независимо от DOM.
- assets: id, name, path, mime_type; пути ресурсов только относительные и без traversal-сегментов.
- У проекта ровно одна главная страница; slug страниц уникальны.

## API проектов
- GET /api/projects — список.
- POST /api/projects — создание.
- GET /api/projects/{id} — открытие.
- PUT /api/projects/{id} — сохранение.
- DELETE /api/projects/{id} — удаление.

## Запуск
launch.vbs → pythonw.exe → main.py → проверка/создание .venv и зависимостей → FastAPI/Uvicorn → окно pywebview.
FastAPI слушает только 127.0.0.1; порт выбирается при запуске. Frontend и API обслуживаются одним backend.

## Модули
Текущий реестр только читает и проверяет modules/*/module.json. Динамическая загрузка — отдельный этап с разрешениями, зависимостями и изоляцией.

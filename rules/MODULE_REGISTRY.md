# Контракт манифеста модуля

Минимальный формат:

```json
{
  "id": "vendor.module-name",
  "name": "Module name",
  "version": "0.1.0",
  "enabled": false,
  "dependencies": []
}
```

ID — уникальный стабильный идентификатор в нижнем регистре. Name — имя для интерфейса. Version — версия. Enabled — состояние. Dependencies — обязательные ID других модулей.

Наличие enabled=true само по себе не разрешает исполнение кода. Поля entrypoint, API version и permissions появятся после утверждения модели безопасности.

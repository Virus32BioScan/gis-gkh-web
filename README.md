# ГИС ЖКХ — Мини веб-интерфейс (exportOrgRegistry)

Минималистичный UI для сборки/подписи/отправки запроса `exportOrgRegistry` через stunnel.
- Клиентская подпись: **CryptoPro Extension for CAdES** (рекомендуется).
- Серверная подпись: **CAdESCOM (CryptoPro CSP)** — опционально.
- Транспорт: HTTP → stunnel → TLS ГОСТ до `api.dom.gosuslugi.ru` (через заголовок Host).

## Быстрый старт
```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8080
```
Открой `http://127.0.0.1:8080`.

Переменные окружения (при необходимости):
```
GIS_TARGET_HOST=api.dom.gosuslugi.ru
GIS_STUNNEL_HOST=127.0.0.1
GIS_STUNNEL_PORT=8080
GIS_SOAP11=0  # 1 для SOAP 1.1
```

## Что внутри
- `POST /api/build/export-org-registry` — сборка Envelope (дата `now()+09:00`, `MessageGUID=uuid4`).
- `POST /api/sign/server` — подпись в CSP (по отпечатку).
- `GET /api/certs` — список сертификатов (`include_machine`, `include_non_valid`, `with_private_key_only`).
- `POST /api/send` — отправка через stunnel (SOAP 1.2 по умолчанию, есть SOAP 1.1 + SOAPAction).

## Требования
- **Python 3.13** (OK и для 3.11+).
- Для серверной подписи: Windows x64, CryptoPro CSP 5.13 + CAdESCOM x64, `pywin32`.
- Для клиентской подписи: установленное расширение **CryptoPro Extension for CAdES** в браузере.

---
© 2025 — внутренний инструмент.

:: push_to_github.cmd — скрипт-шпаргалка (Windows CMD)
@echo off
setlocal

REM === 1) Создать новый пустой репозиторий на GitHub ===
REM Способ А (через веб): https://github.com/new  -> Repository name: gis-gkh-web
REM Способ Б (через GitHub CLI):
REM   gh auth login
REM   gh repo create gis-gkh-web --private --source . --remote origin --push

REM === 2) Локальная инициализация и пуш ===
git init
git add .
git commit -m "init: minimal GIS GKH web UI (exportOrgRegistry)"
REM Замените URL на ваш (SSH или HTTPS):
git remote add origin https://github.com/<your-user>/gis-gkh-web.git
git branch -M main
git push -u origin main

echo Done.

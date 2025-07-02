@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: Настройки
set "REPO=punshofficial/mass-alligator"
set "ASSET=MassAlligator.zip"
set "API_URL=https://api.github.com/repos/%REPO%/releases/latest"
set "UA=MassAlligatorUpdater/1.0"

echo Проверяю обновления...

:: 1) Получаем последнюю версию
for /f "delims=" %%A in ('powershell -NoProfile -Command "(Invoke-RestMethod -Uri '%API_URL%' -Headers @{ 'User-Agent'='%UA%'; 'Accept'='application/vnd.github.v3+json' }).tag_name"') do (
  set "LATEST=%%A"
)

if not defined LATEST (
  echo Ошибка: не удалось узнать последнюю версию.
  pause
  goto :EOF
)

:: 2) Читаем локальную версию
if exist version.txt (
  set /p LOCAL=<version.txt
) else (
  set "LOCAL="
)

echo Локальная версия: !LOCAL!
echo Последняя версия: !LATEST!

if /i "!LATEST!"=="!LOCAL!" (
  echo Уже актуально, обновлений нет.
  pause
  goto :EOF
)

echo Обновление есть, качаю версию !LATEST!...

:: 3) Берём URL ZIP
for /f "delims=" %%A in ('powershell -NoProfile -Command "$r=(Invoke-RestMethod -Uri '%API_URL%' -Headers @{ 'User-Agent'='%UA%'; 'Accept'='application/vnd.github.v3+json' }); ($r.assets | Where-Object Name -EQ '%ASSET%' | Select-Object -ExpandProperty browser_download_url)"') do (
  set "DOWNLOAD_URL=%%A"
)

if not defined DOWNLOAD_URL (
  echo Ошибка: не найден asset %ASSET%.
  pause
  goto :EOF
)

:: 4) Скачиваем ZIP
powershell -NoProfile -Command "Invoke-WebRequest -Uri '%DOWNLOAD_URL%' -OutFile update.zip -Headers @{ 'User-Agent'='%UA%'; 'Accept'='application/octet-stream' }"

if not exist update.zip (
  echo Не удалось скачать update.zip
  pause
  goto :EOF
)

:: 5) Резервная копия (опционально)
mkdir backup 2>nul
xcopy /e /i /y . backup >nul

:: 6) Распаковываем
powershell -NoProfile -Command "Expand-Archive -Path update.zip -DestinationPath . -Force"

:: 7) Обновляем версию
(echo !LATEST!)>version.txt

:: 8) Удаляем временные файлы
del update.zip

echo Обновлено до версии !LATEST!.
pause

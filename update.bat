@echo off
setlocal enabledelayedexpansion

:: Репозиторий и имя asset
set "REPO=YOUR_OWNER/YOUR_REPO"
set "ASSET_NAME=MassAlligator.zip"
set "API_URL=https://api.github.com/repos/%REPO%/releases/latest"

:: 1) Получаем последнюю версию с GitHub
for /f "usebackq delims=" %%A in (`
  powershell -Command "(Invoke-RestMethod -UseBasicParsing '%API_URL%').tag_name"
`) do set "LATEST=%%A"

:: 2) Читаем локальную версию
if exist version.txt (
  set /p LOCAL=<version.txt
) else (
  set "LOCAL=none"
)

echo Локальная версия: %LOCAL%
echo Последняя версия:  %LATEST%

if /i "%LATEST%"=="%LOCAL%" (
  echo Уже актуально, обновлений нет.
  goto :EOF
)

echo Обнаружено обновление. Скачиваем версию %LATEST%...

:: 3) Получаем URL скачивания нужного ZIP
for /f "usebackq delims=" %%A in (`
  powershell -Command ^
    "(Invoke-RestMethod -UseBasicParsing '%API_URL%').assets ^| Where-Object { $_.name -eq '%ASSET_NAME%' } ^| Select-Object -ExpandProperty browser_download_url"
`) do set "DOWNLOAD_URL=%%A"

if "%DOWNLOAD_URL%"=="" (
  echo Ошибка: не найден asset %ASSET_NAME% в релизе %LATEST%.
  goto :EOF
)

:: 4) Скачиваем ZIP
powershell -Command "Invoke-WebRequest -UseBasicParsing '%DOWNLOAD_URL%' -OutFile update.zip"

if not exist update.zip (
  echo Не удалось скачать update.zip
  goto :EOF
)

:: 5) Резервная копия (опционально)
mkdir backup 2>nul
xcopy /e /i /y . backup >nul

:: 6) Распаковываем обновление поверх
powershell -Command "Expand-Archive -Path update.zip -DestinationPath . -Force"

:: 7) Обновляем версию
echo %LATEST%>version.txt

:: 8) Убираем временный файл
del update.zip

echo Обновление до версии %LATEST% завершено!
pause

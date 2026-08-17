@echo off
chcp 65001 >nul
title ВелоЦентр

:: Проверяем Python
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  Установка компонентов... Подождите 2-3 минуты.
    echo.

    :: Скачиваем и устанавливаем Python тихо
    curl -L -o "%TEMP%\python_installer.exe" "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe" >nul 2>&1
    if errorlevel 1 (
        powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe' -OutFile '%TEMP%\python_installer.exe'" >nul 2>&1
    )
    "%TEMP%\python_installer.exe" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0 >nul 2>&1
    del "%TEMP%\python_installer.exe" >nul 2>&1

    :: Обновляем PATH
    set "PATH=%LOCALAPPDATA%\Programs\Python\Python311;%LOCALAPPDATA%\Programs\Python\Python311\Scripts;%PATH%"

    :: Проверяем ещё раз
    python --version >nul 2>&1
    if errorlevel 1 (
        echo.
        echo  Не удалось установить компоненты автоматически.
        echo  Позвоните: +7 (920) 497-47-87
        echo.
        pause
        exit /b 1
    )
)

:: Устанавливаем зависимости при первом запуске
if not exist ".venv" (
    echo.
    echo  Первоначальная настройка... Подождите 1-2 минуты.
    echo.
    python -m venv .venv
    call .venv\Scripts\activate.bat
    pip install -r requirements.txt --quiet --disable-pip-version-check
    echo.
    echo  Готово! Запускаю...
    echo.
)

:: Запускаем
call .venv\Scripts\activate.bat
start "" "http://localhost:8501"
streamlit run app.py --server.headless true --browser.gatherUsageStats false --server.port 8501
pause

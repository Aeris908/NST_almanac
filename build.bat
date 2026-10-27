@echo off
chcp 65001 > nul
echo ===================================================
echo   BUILD ALL NEKKETSU ALMANAC & DEPLOY BUNDLE
echo ===================================================
echo.

set PYTHON_CMD=

where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    python -c "import sys; print(sys.version)" >nul 2>nul
    if %ERRORLEVEL% EQU 0 set PYTHON_CMD=python
)

if "%PYTHON_CMD%"=="" (
    where py >nul 2>nul
    if %ERRORLEVEL% EQU 0 set PYTHON_CMD=py
)

if "%PYTHON_CMD%"=="" if exist "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" set PYTHON_CMD="%LOCALAPPDATA%\Programs\Python\Python314\python.exe"
if "%PYTHON_CMD%"=="" if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" set PYTHON_CMD="%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
if "%PYTHON_CMD%"=="" if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set PYTHON_CMD="%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if "%PYTHON_CMD%"=="" if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set PYTHON_CMD="%LOCALAPPDATA%\Programs\Python\Python311\python.exe"

if "%PYTHON_CMD%"=="" (
    echo [ОШИБКА] Python не найден! Установите Python или добавьте его в PATH.
    pause
    exit /b 1
)

%PYTHON_CMD% build_all.py

echo.
echo Сборка завершена! Папка deploy/ готова к загрузке на хостинг.
echo.
pause

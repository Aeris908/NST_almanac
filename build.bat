@echo off
chcp 65001 > nul
echo ===================================================
echo   BUILD ALL NEKKETSU ALMANAC & DEPLOY BUNDLE
echo ===================================================
echo.
python build_all.py
if %ERRORLEVEL% NEQ 0 (
  py build_all.py
)
echo.
echo Сборка завершена! Папка deploy/ готова к загрузке на хостинг.
echo.
pause

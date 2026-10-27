@echo off
chcp 65001 > nul
echo ===================================================
echo   NEKKETSU AUDIO LIBRARY SCANNER (MP3 & ID3 TAGS)
echo ===================================================
echo.
python scan_audio.py
if %ERRORLEVEL% NEQ 0 (
  py scan_audio.py
)
echo.
echo Все треки успешно просканированы и добавлены в плейлисты!
echo.
pause

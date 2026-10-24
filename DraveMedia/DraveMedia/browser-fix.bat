@echo off
title DraveMedia - ingebouwde browser controleren
cd /d "%~dp0"
echo ============================================================
echo   DraveMedia - ingebouwde browser (QtWebEngine) controleren
echo ============================================================
echo.
if not exist ".venv\Scripts\python.exe" (
  echo Er is nog geen .venv. Start eerst run.bat een keer.
  echo.
  pause & exit /b 1
)
echo Python die DraveMedia gebruikt:
".venv\Scripts\python.exe" --version
echo.
echo Ingebouwde browser installeren (PyQt6-WebEngine)...
".venv\Scripts\python.exe" -m pip install --only-binary=:all: PyQt6-WebEngine
echo.
".venv\Scripts\python.exe" -c "import PyQt6.QtWebEngineWidgets; print('RESULTAAT: OK - de ingebouwde browser is beschikbaar.')" 2>nul
if errorlevel 1 (
  echo RESULTAAT: NIET GELUKT.
  echo Er is waarschijnlijk nog geen PyQt6-WebEngine voor jouw Python-versie.
  echo Oplossing: installeer Python 3.13 ^(van python.org^) en draai daarna
  echo herstel.bat + run.bat opnieuw. Tot die tijd werkt 'Bekijk in browser'.
)
echo.
pause

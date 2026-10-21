@echo off
title DraveMedia - .exe bouwen (onefolder)
cd /d "%~dp0"
echo ==================================================
echo    DraveMedia - een .exe bouwen (met ingebouwde browser)
echo ==================================================
echo.
set "BV=.build-venv"
set "PYEXE="
for %%V in (3.13 3.12 3.11 3.10) do (
  if not defined PYEXE ( py -%%V -c "import sys" >nul 2>&1 && set "PYEXE=py -%%V" )
)
if not defined PYEXE ( python --version >nul 2>&1 && set "PYEXE=python" )
if not defined PYEXE ( echo [FOUT] Geen Python 3.10-3.13 gevonden. & pause & exit /b 1 )

echo [1/3] Bouw-omgeving voorbereiden...
if not exist "%BV%\Scripts\python.exe" ( %PYEXE% -m venv "%BV%" )
if errorlevel 1 ( echo [FOUT] venv mislukt - draai eventueel herstel-bouw.bat. & pause & exit /b 1 )
set "VPY=%BV%\Scripts\python.exe"

echo [2/3] Benodigdheden installeren...
"%VPY%" -m pip install --upgrade pip >nul 2>&1
"%VPY%" -m pip install --only-binary=:all: pyinstaller PyQt6 PyQt6-Qt6 PyQt6-WebEngine Pillow
if errorlevel 1 (
  echo [FOUT] Installatie mislukt. Verwijder de map .build-venv en probeer opnieuw.
  pause & exit /b 1
)

echo [3/3] De app bouwen...
"%VPY%" maak_icoon.py
"%VPY%" -m PyInstaller --noconfirm --clean dravemedia.spec
if errorlevel 1 ( echo [FOUT] Bouwen mislukt. & pause & exit /b 1 )

ie4uinit.exe -show >nul 2>&1
ie4uinit.exe -ClearIconCache >nul 2>&1

echo.
echo KLAAR! Je app staat hier:
echo    dist\DraveMedia\   ^(de hele map - DraveMedia.exe + onderdelen^)
echo.
echo BELANGRIJK: houd DraveMedia.exe SAMEN met de map _internal.
echo Voor op je bureaublad: maak een snelkoppeling naar DraveMedia.exe.
echo dravemedia_config.json maakt de app zelf aan naast de .exe.
echo.
echo Zie je nog het oude icoon? Dat is de Windows-cache:
echo  - sleep de map naar een andere plek, of log uit/in.
echo.
pause

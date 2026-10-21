@echo off
title DraveMedia - herstel
cd /d "%~dp0"
echo Dit verwijdert de map .venv zodat alles opnieuw geinstalleerd wordt.
pause
if exist ".venv" rmdir /s /q ".venv"
echo Klaar. Start DraveMedia weer met run.bat.
pause

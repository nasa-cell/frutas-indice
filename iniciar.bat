@echo off
cd /d "%~dp0"
if not exist entorno\Scripts\python.exe (
  echo Instalando lo necesario por primera vez, espera...
  py -3.12 -m venv entorno || python -m venv entorno
  entorno\Scripts\python.exe -m pip install -r codigo\requirements.txt
)
start "" entorno\Scripts\pythonw.exe codigo\juego.py

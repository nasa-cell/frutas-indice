#!/bin/sh
# Arma el instalador: 1) juego.exe con PyInstaller  2) imágenes  3) Inno Setup.
# Resultado en "pc instalador/". Carpeta de trabajo: C:/herramientas/compilacion/corte-frutal
set -e
cd "$(dirname "$0")/.."
P=$(pwd -W)
E=/c/herramientas/compilacion/corte-frutal
entorno/Scripts/python.exe -m PyInstaller --noconfirm --clean --windowed --name "Corte Frutal" \
  --icon "$P/aplicacion/icono.ico" --paths "$P/codigo" --add-data "$P/recursos;recursos" \
  --collect-data mediapipe --collect-binaries mediapipe \
  --distpath $E/dist --workpath $E/build --specpath $E "$P/codigo/juego.py"
entorno/Scripts/python.exe aplicacion/crear_imagenes.py
cd aplicacion && /c/herramientas/innosetup/ISCC.exe -Q instalador.iss

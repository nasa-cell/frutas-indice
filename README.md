**[⬇ Descargar instalador para Windows (Corte Frutal 1.0.0)](https://github.com/nasa-cell/frutas-indice/releases/latest/download/Instalar.Corte.Frutal.1.0.0.exe)**

# Corte Frutal

Juego de visión computacional: cortas frutas moviendo tu **dedo índice** frente a la cámara, sin mouse ni teclado.

## Cómo funciona

1. **OpenCV** abre la cámara y entrega cada imagen.
2. **MediaPipe** (Hand Landmarker) encuentra los 21 puntos de la mano; el punto 8 es la punta del índice.
3. El dedo se suaviza con un filtro *One Euro* (sin temblor y sin retraso) y deja una estela de espada.
4. Si la estela cruza una fruta, se corta en dos mitades, salpica jugo y suma puntos.
5. **Pygame** dibuja el juego y los sonidos; **NumPy** hace las cuentas, los brillos y los sonidos.

La cámara y el detector trabajan en un hilo aparte (`camara.py`), así el juego va a 60 cuadros por segundo aunque la cámara dé 30.

Para jugar desde lejos, el programa hace **zoom digital** sobre la mano (se ve un recuadro dorado en la cámara) y ajusta la zona de juego: lejos, con mover poco la mano llegas a toda la pantalla.

## Reglas

- 60 segundos y 3 vidas.
- Cada fruta vale 1 punto. Cortar 3 o más de un solo trazo da combo y puntos extra.
- La bomba quita 1 vida. Si una fruta se cae sin cortar, no pasa nada.
- El récord se guarda en `%APPDATA%\Corte Frutalecord.json` (no se pierde al actualizar ni al desinstalar).
- Para empezar (o jugar otra vez) se corta la fruta grande que aparece abajo.

## Cómo abrirlo

Lo más fácil: descarga el instalador (enlace de arriba), ábrelo y dale a **Instalar**. No necesita internet ni Python.

Desde el código: doble clic en **`iniciar.bat`**. La primera vez instala lo necesario (hace falta internet y Python 3.12).

A mano:

```
py -3.12 -m venv entorno
entorno\Scripts\python.exe -m pip install -r codigo\requirements.txt
entorno\Scripts\python.exe codigo\juego.py
```

Opciones: `--ventana` (ventana de 1280×720, para pruebas) y `--sin-camara` (empieza con la cámara apagada).

## Botones y teclas

Encima del cuadro de la cámara hay dos botones. Se activan con **clic** o dejando el **dedo 1 segundo encima** (un anillo dorado se llena):

- **Pantalla completa / salir de pantalla completa** (la ventana ocupa el 85 % de la pantalla).
- **Encender / apagar cámara**. Con la cámara apagada se sigue jugando con el mouse.

Teclas: **Enter/Espacio** jugar · **Esc** volver o salir · **F11** pantalla completa.

Mientras el juego está abierto, Windows no apaga la pantalla ni suspende la computadora (se juega sin tocar mouse ni teclado). Al cerrar el juego todo vuelve a la normalidad.

## Carpetas

```
juego-frutas/
├─ iniciar.bat        doble clic para jugar
├─ LEEME.md
├─ codigo/            el programa (.py) y requirements.txt
├─ recursos/          dibujos, letra y modelo de manos
├─ datos/             record.json
├─ maqueta/           maquetas HTML del diseño
├─ contexto/          notas del proyecto y pendientes
└─ entorno/           Python con las librerías
```

## Archivos de `codigo/`

| Archivo | Qué hace |
|---|---|
| `juego.py` | Reglas, puntos, combos, pantallas y bucle principal |
| `interfaz.py` | Paneles, tarjetas, cuadro de la cámara, estela y botones |
| `camara.py` | Cámara (OpenCV) + detector de manos (MediaPipe), zoom y filtro del dedo |
| `frutas.py` | Frutas, bombas, mitades cortadas, gotas y manchas de jugo |
| `fondo.py` | Fondo de noche animado: estrellas, estrellas fugaces, luna, niebla y luciérnagas |
| `graficos.py` | Textos con borde, paneles, corazones y brillos |
| `sonidos.py` | Sonidos hechos con código (corte, espada, bomba, combo, inicio, fin) |
| `requirements.txt` | Librerías que necesita el juego |

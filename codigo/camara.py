"""Cámara + MediaPipe en un hilo aparte: lee el dedo índice sin frenar el juego.

- Zoom digital: si la mano está lejos, se recorta la zona de la mano para que
  el detector la vea más grande.
- Zona de juego según la distancia: lejos, moviendo poco la mano se llega a
  toda la pantalla.
- Filtro «One Euro»: quita el temblor cuando el dedo va lento y no agrega
  retraso cuando va rápido.
"""
import math
import threading
import time

import cv2
import numpy as np


def _lim(v, a, b):
    return min(b, max(a, v))


class FiltroEuro:
    def __init__(self, min_corte=1.2, beta=30.0, d_corte=1.0):
        self.min_corte, self.beta, self.d_corte = min_corte, beta, d_corte
        self.x = None
        self.dx = 0.0
        self.t = 0.0

    @staticmethod
    def _alfa(corte, dt):
        return 1 / (1 + 1 / (2 * math.pi * corte * dt))

    def reiniciar(self):
        self.x = None

    def paso(self, valor, t):
        if self.x is None:
            self.x, self.t = valor, t
            return valor
        dt = max(1e-3, t - self.t)
        self.t = t
        d = (valor - self.x) / dt
        self.dx += self._alfa(self.d_corte, dt) * (d - self.dx)
        corte = self.min_corte + self.beta * abs(self.dx)
        self.x += self._alfa(corte, dt) * (valor - self.x)
        return self.x


BUSQUEDA = [(.5, .5, 1), (.5, .45, .62), (.5, .45, .45), (.32, .45, .55), (.68, .45, .55)]


class Camara(threading.Thread):
    def __init__(self, ruta_modelo, indice=0, esperar=None):
        super().__init__(daemon=True)
        self.esperar = esperar     # cámara anterior que todavía se está cerrando
        self.ruta_modelo = ruta_modelo
        self.indice = indice
        self.cerrojo = threading.Lock()
        self.activa = True
        self.estado = "cargando"   # cargando | lista | error
        self.mensaje = "Encendiendo la cámara…"
        self.dedo = None           # (x, y) de 0 a 1 en la pantalla
        self.mano = None           # 21 puntos (x, y) de 0 a 1 en la imagen
        self.zona = (0, 0, 1)
        self.miniatura = None      # imagen chica en espejo (RGB)
        self.fps = 0
        self.aspecto_pantalla = 16 / 9

    def leer(self):
        with self.cerrojo:
            return self.dedo, self.mano, self.zona, self.miniatura, self.fps

    def detener(self):
        self.activa = False

    def _abrir(self):
        cap = cv2.VideoCapture(self.indice, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(self.indice)
        if not cap.isOpened():
            return None
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        cap.set(cv2.CAP_PROP_FPS, 60)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        return cap

    def run(self):
        try:
            self._trabajar()
        except Exception as e:
            self.estado, self.mensaje = "error", f"La cámara se detuvo: {e}"
            with self.cerrojo:
                self.dedo = self.mano = None

    def _trabajar(self):
        if self.esperar is not None and self.esperar.is_alive():
            self.esperar.join(3)   # espera aquí (no en el juego) a que la anterior suelte la cámara
        self.esperar = None
        try:
            import mediapipe as mp
            from mediapipe.tasks.python import BaseOptions, vision
        except Exception as e:
            self.estado, self.mensaje = "error", f"No se pudo cargar MediaPipe: {e}"
            return
        cap = self._abrir()
        if cap is None:
            self.estado, self.mensaje = "error", "No se encontró ninguna cámara conectada"
            return
        self.mensaje = "Cargando el detector de manos…"
        opciones = vision.HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=self.ruta_modelo),
            running_mode=vision.RunningMode.VIDEO, num_hands=1,
            min_hand_detection_confidence=.4, min_hand_presence_confidence=.4, min_tracking_confidence=.4)
        detector = vision.HandLandmarker.create_from_options(opciones)
        self.estado, self.mensaje = "lista", "Cámara lista"

        # lector aparte: siempre se usa la imagen más nueva, nunca una que quedó en cola
        ultimo = {"cuadro": None, "n": 0}
        aviso = threading.Event()

        def leer_camara():
            while self.activa:
                ok, c = cap.read()
                if ok:
                    ultimo["cuadro"], ultimo["n"] = c, ultimo["n"] + 1
                    aviso.set()
                else:
                    time.sleep(.005)
        threading.Thread(target=leer_camara, daemon=True).start()

        fx, fy = FiltroEuro(min_corte=1.5, beta=45.0), FiltroEuro(min_corte=1.5, beta=30.0)
        zona = [.5, .5, 1.0]
        tam_mano = .22
        buscar = 0
        perdida = 0.0
        hay_mano = False
        visto = 0
        previo = previo_nudillo = None  # (x, y, t) del dedo ya filtrado, para calcular su velocidad
        vel = [0.0, 0.0]
        vel_mano = [0.0, 0.0]  # velocidad del nudillo en la imagen, para mover el zoom por delante
        cuadros, t_fps = 0, time.perf_counter()
        t_ultimo = 0
        ADELANTO = .05         # segundos que se adelanta el dedo para tapar el retraso de la cámara

        while self.activa:
            if not aviso.wait(.5) or ultimo["n"] == visto:
                continue
            aviso.clear()
            visto = ultimo["n"]
            cuadro = ultimo["cuadro"]
            ahora = time.perf_counter()
            cuadros += 1
            alto, ancho = cuadro.shape[:2]
            if not hay_mano or perdida:
                b = BUSQUEDA[buscar % len(BUSQUEDA)]
                buscar += 1
                zona = [b[0], b[1], b[2]]
            z = zona[2]
            zx = _lim(zona[0] - z / 2, 0, 1 - z)
            zy = _lim(zona[1] - z / 2, 0, 1 - z)
            x0, y0 = int(zx * ancho), int(zy * alto)
            recorte = cuadro[y0:y0 + int(z * alto), x0:x0 + int(z * ancho)]
            recorte = cv2.resize(recorte, (640, int(640 * alto / ancho)), interpolation=cv2.INTER_AREA)
            rgb = cv2.cvtColor(recorte, cv2.COLOR_BGR2RGB)
            t_ms = max(t_ultimo + 1, int(ahora * 1000))
            t_ultimo = t_ms
            resultado = detector.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), t_ms)

            dedo = None
            mano = None
            if resultado.hand_landmarks:
                mano = [(zx + p.x * z, zy + p.y * z) for p in resultado.hand_landmarks[0]]
                if hay_mano and previo_nudillo:
                    dtm = max(1e-3, ahora - previo_nudillo[2])
                    vel_mano = [(mano[9][0] - previo_nudillo[0]) / dtm, (mano[9][1] - previo_nudillo[1]) / dtm]
                previo_nudillo = (mano[9][0], mano[9][1], ahora)
                hay_mano, perdida = True, 0.0
                t = math.hypot((mano[9][0] - mano[0][0]) * ancho / alto, mano[9][1] - mano[0][1])
                tam_mano += (t - tam_mano) * .04
                # zoom: nunca muy cerrado y siempre centrado donde va a estar la mano
                zona[2] += (_lim(tam_mano * 6.5, .55, 1) - zona[2]) * .15
                zona[0] = mano[9][0] + vel_mano[0] * .06
                zona[1] = mano[9][1] + vel_mano[1] * .06
                rw = _lim(tam_mano * alto / ancho * 7, .28, .78)
                rh = _lim(rw * (ancho / alto) / self.aspecto_pantalla, .25, .85)
                cy = .46
                px, py = mano[8]
                nx = _lim(((1 - px) - (.5 - rw / 2)) / rw, 0, 1)
                ny = _lim((py - (cy - rh / 2)) / rh, 0, 1)
                sx, sy = fx.paso(nx, ahora), fy.paso(ny, ahora)
                if previo:
                    dtp = max(1e-3, ahora - previo[2])
                    vel[0] += ((sx - previo[0]) / dtp - vel[0]) * .6
                    vel[1] += ((sy - previo[1]) / dtp - vel[1]) * .6
                previo = (sx, sy, ahora)
                dedo = (_lim(sx + vel[0] * ADELANTO, 0, 1), _lim(sy + vel[1] * ADELANTO, 0, 1))
            else:
                if not perdida:
                    perdida = ahora
                    buscar = 0   # primero mira la imagen completa
                quieto = ahora - perdida
                if quieto < .12 and previo:
                    # la mano se borró un instante (movimiento rápido): el dedo sigue su camino
                    dedo = (_lim(previo[0] + vel[0] * (quieto + ADELANTO), 0, 1),
                            _lim(previo[1] + vel[1] * (quieto + ADELANTO), 0, 1))
                if quieto > .22:
                    hay_mano = False
                    previo = previo_nudillo = None
                    vel = [0.0, 0.0]
                    vel_mano = [0.0, 0.0]
                    fx.reiniciar()
                    fy.reiniciar()

            mini = cv2.resize(cuadro, (320, int(320 * alto / ancho)), interpolation=cv2.INTER_AREA)
            mini = cv2.cvtColor(cv2.flip(mini, 1), cv2.COLOR_BGR2RGB)
            with self.cerrojo:
                if dedo is not None:
                    self.dedo = dedo
                    if mano:
                        self.mano = mano
                elif not hay_mano:
                    self.dedo, self.mano = None, None
                self.zona = (zx, zy, z)
                self.miniatura = np.ascontiguousarray(mini)
            if ahora - t_fps > 1:
                self.fps = round(cuadros / (ahora - t_fps))
                cuadros, t_fps = 0, ahora
        cap.release()
        detector.close()

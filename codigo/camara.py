"""Cámara + MediaPipe en un hilo aparte: lee el dedo índice sin frenar el juego.

- Zoom digital: si la mano está lejos, se recorta la zona de la mano para que
  el detector la vea más grande.
- Zona de juego según la distancia: lejos, moviendo poco la mano se llega a
  toda la pantalla.
- Filtro «One Euro»: quita el temblor cuando el dedo va lento y no agrega
  retraso cuando va rápido.
- Zona clavada: con el dedo quieto el puntero no se mueve hasta que la mano
  se mueve más o menos 1 cm.
- Mano perdida: se busca con 13 recortes (algunos con más zoom, para manos de
  niño o lejanas) y se prueba también la imagen corregida (luz fuerte o
  contraluz).
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


# recortes para buscar la mano perdida: (centro x, centro y, tamaño). Los de 0,42 y 0,3 encuentran manos chicas
BUSQUEDA = [(.5, .5, 1), (.5, .45, .62)] + [(x, y, .42) for y in (.33, .62) for x in (.25, .5, .75)] +     [(x, y, .3) for y in (.38, .58) for x in (.38, .62)]
AVISO_SIN_MANO = 3.0   # segundos sin ver la mano antes de mostrar el aviso


class Correccion:
    """Aclara u oscurece la imagen y le sube el contraste (luz fuerte o contraluz)."""
    def __init__(self):
        self.clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))

    def aplicar(self, img):
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l = lab[:, :, 0]
        media = float(l.mean()) / 255
        l = self.clahe.apply(l)
        g = math.log(.47) / math.log(_lim(media, .05, .95))   # lleva el brillo medio a 0,47
        tabla = np.clip(((np.arange(256) / 255) ** g) * 255, 0, 255).astype(np.uint8)
        lab[:, :, 0] = cv2.LUT(l, tabla)
        return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

    @staticmethod
    def luz_dificil(img):
        """True con mucha luz (partes quemadas) o contraluz/oscuridad (mucha imagen negra)."""
        g = cv2.cvtColor(cv2.resize(img, (160, 90), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)
        quemado = float((g > 245).mean())
        oscuro = float((g < 25).mean())
        media = float(g.mean())
        return quemado > .10 or oscuro > .30 or media > 175 or media < 60


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
        self.sin_mano = False      # True si hace rato que no ve la mano (para el aviso)
        self.tramo = 0             # sube cuando el dedo reaparece lejos: el juego empieza una línea nueva

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
            base_options=BaseOptions(model_asset_buffer=open(self.ruta_modelo, "rb").read()),   # buffer: funciona aunque la carpeta tenga tildes o ñ
            running_mode=vision.RunningMode.VIDEO, num_hands=1,
            min_hand_detection_confidence=.2, min_hand_presence_confidence=.2, min_tracking_confidence=.3)
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

        fx, fy = FiltroEuro(min_corte=.9, beta=30.0), FiltroEuro(min_corte=.9, beta=22.0)
        ancla = None           # punto clavado del puntero (zona clavada)
        zona = [.5, .5, 1.0]
        correccion = Correccion()
        corregir = False       # True si la mano se encontró en la imagen corregida
        dificil = False        # luz difícil: al buscar se prueba también la imagen corregida
        t_sin_mano = time.perf_counter()
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
        candidata = None       # nudillo (x, y) de una mano vista al buscar; se acepta si el cuadro siguiente la confirma
        ultimo_dedo = None     # último dedo entregado al juego, para saber si reaparece lejos
        alcance = None         # [izq, der, arriba, abajo] que la mano alcanzó hace poco (imagen en espejo)
        t_alcance = None
        punta = None           # (dx, dy) de la punta del índice respecto a su nudillo (punto 5), ya revisada
        punta_dudosa = None    # punta que saltó sola; se acepta si el cuadro siguiente la repite
        ADELANTO = .05         # segundos que se adelanta el dedo para tapar el retraso de la cámara
        RAPIDO = .6            # desde esta rapidez (pantallas por segundo) el adelanto empieza a actuar

        while self.activa:
            if not aviso.wait(.5) or ultimo["n"] == visto:
                continue
            aviso.clear()
            visto = ultimo["n"]
            cuadro = ultimo["cuadro"]
            ahora = time.perf_counter()
            cuadros += 1
            alto, ancho = cuadro.shape[:2]
            buscando = not hay_mano or perdida
            if buscando and candidata is None:   # con una candidata se repite el mismo recorte para confirmarla
                if cuadros % 15 == 1:
                    dificil = Correccion.luz_dificil(cuadro)
                if dificil:
                    # cada recorte se prueba normal y corregido: normal, corregido, siguiente recorte…
                    b = BUSQUEDA[(buscar // 2) % len(BUSQUEDA)]
                    corregir = buscar % 2 == 1
                else:
                    b = BUSQUEDA[buscar % len(BUSQUEDA)]
                    corregir = False
                buscar += 1
                zona = [b[0], b[1], b[2]]
            z = zona[2]
            zx = _lim(zona[0] - z / 2, 0, 1 - z)
            zy = _lim(zona[1] - z / 2, 0, 1 - z)
            x0, y0 = int(zx * ancho), int(zy * alto)
            recorte = cuadro[y0:y0 + int(z * alto), x0:x0 + int(z * ancho)]
            recorte = cv2.resize(recorte, (640, int(640 * alto / ancho)), interpolation=cv2.INTER_AREA)
            if corregir:
                recorte = correccion.aplicar(recorte)
            rgb = cv2.cvtColor(recorte, cv2.COLOR_BGR2RGB)
            t_ms = max(t_ultimo + 1, int(ahora * 1000))
            t_ultimo = t_ms
            resultado = detector.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), t_ms)

            dedo = None
            mano = None
            nuevo_tramo = False
            if resultado.hand_landmarks:
                mano = [(zx + p.x * z, zy + p.y * z) for p in resultado.hand_landmarks[0]]
                if buscando:
                    # una mano vista una sola vez al buscar puede ser falsa (cara, sombra, otro objeto):
                    # se acepta solo si el cuadro siguiente la ve en el mismo sitio
                    nudillo = mano[9]
                    t_vista = math.hypot((mano[9][0] - mano[0][0]) * ancho / alto, mano[9][1] - mano[0][1])
                    cerca = (hay_mano and previo_nudillo and ahora - perdida < .22 and
                             math.hypot(nudillo[0] - previo_nudillo[0], nudillo[1] - previo_nudillo[1]) < t_vista * 2)
                    if cerca:
                        candidata = None   # se perdió hace nada y vuelve cerca: es la misma mano
                    elif candidata is None or math.hypot(nudillo[0] - candidata[0], nudillo[1] - candidata[1]) > max(.08, t_vista * 2.5):
                        candidata = nudillo
                        mano = None
                    else:
                        candidata = None
            elif candidata is not None:
                candidata = None   # no se confirmó: se sigue buscando
            if mano:
                reaparece = bool(perdida)
                if reaparece:
                    vel_mano = [0.0, 0.0]   # tras perderla, la distancia al último nudillo no es velocidad real
                elif hay_mano and previo_nudillo:
                    dtm = max(1e-3, ahora - previo_nudillo[2])
                    vel_mano = [(mano[9][0] - previo_nudillo[0]) / dtm, (mano[9][1] - previo_nudillo[1]) / dtm]
                previo_nudillo = (mano[9][0], mano[9][1], ahora)
                hay_mano, perdida = True, 0.0
                t_sin_mano = ahora
                t = math.hypot((mano[9][0] - mano[0][0]) * ancho / alto, mano[9][1] - mano[0][1])
                tam_mano += (t - tam_mano) * .04
                # zoom: nunca muy cerrado y siempre centrado donde va a estar la mano
                zona[2] += (_lim(tam_mano * 6.5, .55, 1) - zona[2]) * .15
                # el recorte solo se mueve si la mano sale de un margen: así no persigue el temblor
                ox = mano[9][0] + vel_mano[0] * .06 - zona[0]
                oy = mano[9][1] + vel_mano[1] * .06 - zona[1]
                dist = math.hypot(ox, oy)
                margen = tam_mano * .35
                if dist > margen:
                    zona[0] += ox * (dist - margen) / dist
                    zona[1] += oy * (dist - margen) / dist
                rw = _lim(tam_mano * alto / ancho * 7, .28, .78)
                rh = _lim(rw * (ancho / alto) / self.aspecto_pantalla, .25, .85)
                cy = .46
                # con el índice apuntando a la cámara la punta se ve corta y el detector la hace saltar
                # aunque la mano esté quieta: un salto de la punta sola se acepta solo si se repite
                base = mano[5]
                p = (mano[8][0] - base[0], mano[8][1] - base[1])
                if punta is None or reaparece:
                    punta, punta_dudosa = p, None
                elif math.hypot((p[0] - punta[0]) * ancho / alto, p[1] - punta[1]) > tam_mano * .5:
                    if punta_dudosa and math.hypot((p[0] - punta_dudosa[0]) * ancho / alto, p[1] - punta_dudosa[1]) < tam_mano * .3:
                        punta, punta_dudosa = p, None
                    else:
                        punta_dudosa = p
                else:
                    punta, punta_dudosa = p, None
                px, py = base[0] + punta[0], base[1] + punta[1]
                # zona que se ajusta al alcance real: si la mano llega más allá del borde, la zona crece
                # hasta ahí (sin eso el dedo quedaba pegado al borde); cuando no, vuelve sola en unos 6 s
                base_z = [.5 - rw / 2, .5 + rw / 2, cy - rh / 2, cy + rh / 2]
                mx = 1 - px
                if alcance is None:
                    alcance, t_alcance = list(base_z), ahora
                dta = min(.2, ahora - t_alcance)
                t_alcance = ahora
                for k, v in enumerate((mx, mx, py, py)):
                    fuera = v < alcance[k] if k in (0, 2) else v > alcance[k]
                    if fuera:
                        alcance[k] += (v - alcance[k]) * .35
                    alcance[k] += (base_z[k] - alcance[k]) * min(1, dta / 6)
                zi, zd = min(base_z[0], alcance[0]), max(base_z[1], alcance[1])
                za, zb = min(base_z[2], alcance[2]), max(base_z[3], alcance[3])
                zi, zd = max(zi, .02), min(zd, .98)
                za, zb = max(za, .02), min(zb, .98)
                nx = _lim((mx - zi) / (zd - zi), 0, 1)
                ny = _lim((py - za) / (zb - za), 0, 1)
                rw, rh = zd - zi, zb - za
                if reaparece and ultimo_dedo and math.hypot(nx - ultimo_dedo[0], ny - ultimo_dedo[1]) > .1:
                    # volvió lejos de donde quedó: el dedo salta ahí sin arrastrar una línea por el medio
                    fx.reiniciar()
                    fy.reiniciar()
                    ancla = previo = None
                    vel = [0.0, 0.0]
                    nuevo_tramo = True
                sx, sy = fx.paso(nx, ahora), fy.paso(ny, ahora)
                # zona clavada de unos 1 cm de mano (la mano mide unos 9 cm de muñeca a nudillo)
                cm = tam_mano / 9
                rx, ry = cm * alto / ancho / rw, cm / rh
                if ancla is None:
                    ancla = [sx, sy]
                dz = math.hypot((sx - ancla[0]) / rx, (sy - ancla[1]) / ry)
                if dz > 1:
                    ancla[0] += (sx - ancla[0]) * (dz - 1) / dz
                    ancla[1] += (sy - ancla[1]) * (dz - 1) / dz
                sx, sy = ancla
                if previo:
                    dtp = max(1e-3, ahora - previo[2])
                    vel[0] += ((sx - previo[0]) / dtp - vel[0]) * .6
                    vel[1] += ((sy - previo[1]) / dtp - vel[1]) * .6
                previo = (sx, sy, ahora)
                rapidez = math.hypot(vel[0], vel[1])
                adelanto = ADELANTO * _lim((rapidez - RAPIDO) / RAPIDO, 0, 1)   # lento: sin adelanto, no agranda el temblor
                dedo = (_lim(sx + vel[0] * adelanto, 0, 1), _lim(sy + vel[1] * adelanto, 0, 1))
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
                    corregir = False
                    previo = previo_nudillo = None
                    punta = punta_dudosa = None
                    vel = [0.0, 0.0]
                    vel_mano = [0.0, 0.0]
                    fx.reiniciar()
                    fy.reiniciar()
                    ancla = None

            mini = cv2.resize(cuadro, (320, int(320 * alto / ancho)), interpolation=cv2.INTER_AREA)
            mini = cv2.cvtColor(cv2.flip(mini, 1), cv2.COLOR_BGR2RGB)
            with self.cerrojo:
                if nuevo_tramo:
                    self.tramo += 1
                if dedo is not None:
                    self.dedo = ultimo_dedo = dedo
                    if mano:
                        self.mano = mano
                elif not hay_mano:
                    self.dedo, self.mano = None, None
                    ultimo_dedo = None
                self.zona = (zx, zy, z)
                self.sin_mano = ahora - t_sin_mano > AVISO_SIN_MANO
                self.miniatura = np.ascontiguousarray(mini)
            if ahora - t_fps > 1:
                self.fps = round(cuadros / (ahora - t_fps))
                cuadros, t_fps = 0, ahora
        cap.release()
        detector.close()

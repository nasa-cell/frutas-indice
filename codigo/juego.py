"""Corte Frutal: corta frutas con tu dedo índice frente a la cámara.

Teclas: Enter/Espacio = jugar · Esc = volver/salir · F11 = pantalla completa
Opciones: --ventana (1280×720, para pruebas) · --sin-camara (empieza con la cámara apagada)
"""
import ctypes
import json
import math
import os
import random
import sys
import time

if getattr(sys, "frozen", False):   # juego instalado: los recursos van junto al .exe
    CARPETA_PROYECTO = sys._MEIPASS
else:
    CARPETA_PROYECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(CARPETA_PROYECTO)
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

import graficos as gr
import interfaz
import sonidos
from camara import Camara
from fondo import Fondo
from frutas import Fruta, Gota, Imagenes, Mancha, Mitad

# El récord vive en la carpeta del usuario: no se pierde al actualizar o desinstalar.
ARCHIVO_RECORD = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "Corte Frutal", "record.json")
RECORD_ANTIGUO = os.path.join(CARPETA_PROYECTO, "datos", "record.json")
MODELO_MANOS = os.path.join("recursos", "modelo", "hand_landmarker.task")


def leer_record():
    if not os.path.exists(ARCHIVO_RECORD) and os.path.exists(RECORD_ANTIGUO):
        try:
            with open(RECORD_ANTIGUO, encoding="utf-8") as f:
                guardar_record(int(json.load(f).get("record", 0)))
        except (OSError, ValueError):
            pass
    try:
        with open(ARCHIVO_RECORD, encoding="utf-8") as f:
            return int(json.load(f).get("record", 0))
    except (OSError, ValueError):
        return 0


def pantalla_siempre_encendida(activar):
    """Evita que Windows apague la pantalla o suspenda el PC mientras se juega
    (sin mouse ni teclado, Windows creería que nadie lo está usando)."""
    if sys.platform != "win32":
        return
    ES_CONTINUOUS, ES_SYSTEM_REQUIRED, ES_DISPLAY_REQUIRED = 0x80000000, 0x00000001, 0x00000002
    estado = ES_CONTINUOUS | (ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED if activar else 0)
    try:
        ctypes.windll.kernel32.SetThreadExecutionState(estado)
    except (AttributeError, OSError):
        pass


def guardar_record(valor):
    try:
        os.makedirs(os.path.dirname(ARCHIVO_RECORD), exist_ok=True)
        with open(ARCHIVO_RECORD, "w", encoding="utf-8") as f:
            json.dump({"record": valor}, f)
    except OSError:
        pass


class Juego:
    DURACION = 60
    VIDAS = 3

    def __init__(self, sin_camara=False, ventana=None):
        if sys.platform == "win32":
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except (AttributeError, OSError):
                pass
        pygame.mixer.pre_init(44100, -16, 2, 512)
        pygame.init()
        pygame.display.set_caption("Corte Frutal")
        self.completa = ventana is None
        ancho, alto = pygame.display.get_desktop_sizes()[0]
        self.tam_ventana = ventana or (int(ancho * .85), int(alto * .85))   # ventana grande, centrada
        self.abrir_ventana()
        try:
            self.sonidos = sonidos.crear()
        except pygame.error:
            self.sonidos = {}
        self.imagenes = Imagenes()
        self.botones = interfaz.Botones()
        self.camara = None
        if not sin_camara:
            self.encender_camara()
        self.record = leer_record()
        self.pantalla = "inicio"
        self.t = 0.0
        self.reloj = pygame.time.Clock()
        self.dedo = None
        self.objetivo = None
        self.ult_espada = 0.0
        self.reiniciar()
        self.boton_fruta = None
        self.poner_boton_fruta()

    # ---------- ventana, cámara y botones ----------
    def abrir_ventana(self):
        # pantalla completa = ventana sin bordes del tamaño del monitor
        # (no cambia el modo del monitor, así la pantalla no se pone negra)
        if self.completa:
            ancho, alto = pygame.display.get_desktop_sizes()[0]
            self.sup = pygame.display.set_mode((ancho, alto), pygame.NOFRAME)
            posicion = (0, 0)
        else:
            self.sup = pygame.display.set_mode(self.tam_ventana)
            ancho, alto = pygame.display.get_desktop_sizes()[0]
            posicion = ((ancho - self.tam_ventana[0]) // 2, max(0, (alto - self.tam_ventana[1]) // 2))
        try:
            from pygame._sdl2.video import Window
            Window.from_display_module().position = posicion
        except (ImportError, AttributeError, pygame.error):
            pass
        self.W, self.H = self.sup.get_size()
        self.K = max(.6, min(1.6, min(self.W, self.H) / 700))
        self.s = max(.75, min(1.6, self.K * 1.05))
        self.G = 900 * self.K
        self.TOP = int(16 * self.s)
        self.fondo = Fondo(self.W, self.H)
        self.corazones = (gr.corazon(10 * self.s, True), gr.corazon(10 * self.s, False))
        if getattr(self, "camara", None):
            self.camara.aspecto_pantalla = self.W / self.H

    def cambiar_pantalla_completa(self):
        self.completa = not self.completa
        self.abrir_ventana()
        self.poner_boton_fruta()
        self.dedo = self.objetivo = None
        self.rastro = []

    def encender_camara(self):
        self.camara = Camara(MODELO_MANOS, esperar=getattr(self, "camara_vieja", None))
        self.camara.aspecto_pantalla = self.W / self.H
        self.camara.start()

    def apagar_camara(self):
        if self.camara:
            self.camara.detener()
            self.camara_vieja = self.camara
        self.camara = None
        self.dedo = self.objetivo = None
        self.rastro = []

    def accion_boton(self, nombre):
        self.tocar("combo")
        if nombre == "pantalla":
            self.cambiar_pantalla_completa()
        elif self.camara:
            self.apagar_camara()
        else:
            self.encender_camara()

    def tocar(self, nombre):
        s = self.sonidos.get(nombre)
        if s:
            s.play()

    # ---------- estado ----------
    def reiniciar(self):
        self.frutas, self.mitades, self.gotas, self.manchas, self.textos, self.rastro = [], [], [], [], [], []
        self.puntos, self.vidas, self.tiempo = 0, self.VIDAS, float(self.DURACION)
        self.combo, self.mejor_combo, self.ult_corte = 0, 0, 0.0
        self.prox_ola = .6
        self.temblor = 0.0
        self.ult_tic = self.DURACION

    def ir_a(self, nombre):
        self.pantalla = nombre
        if nombre == "juego":
            self.reiniciar()
            self.tocar("inicio")
        else:
            self.frutas = []
            self.prox_ola = .4
        self.poner_boton_fruta()

    def poner_boton_fruta(self):
        """Fruta grande que hay que cortar para empezar (así no hace falta mouse)."""
        if self.pantalla == "juego":
            self.boton_fruta = None
            return
        f = Fruta(self.imagenes, self.W / 2, self.H * .74, 0, 0, self.K * 1.5)
        f.vr = 25
        self.boton_fruta = f

    # ---------- frutas ----------
    def ola(self):
        """Las frutas salen repartidas en carriles a lo ancho y suben hasta debajo de los paneles."""
        n = random.randint(3, 4) if random.random() < .25 else random.randint(1, 2)
        carriles = 5 if self.W < 600 else 8
        ancho = self.W * .84 / carriles
        orden = random.sample(range(carriles), carriles)
        techo = self.TOP + 135 * self.s
        piso = max(techo + 40, self.H * .52)
        for i in range(n):
            xd = self.W * .08 + ancho * (orden[i % carriles] + .5) + random.uniform(-.3, .3) * ancho
            x0 = min(self.W * .95, max(self.W * .05, xd + random.uniform(-.1, .1) * self.W))
            pico = random.uniform(techo, piso)
            vy = -math.sqrt(2 * self.G * (self.H + 40 * self.K - pico))
            vx = (xd - x0) / (-vy / self.G)
            bomba = self.pantalla == "juego" and random.random() < .12
            f = Fruta(self.imagenes, x0, self.H + 60 * self.K, vx, vy, self.K, bomba)
            f.espera = i * random.uniform(.09, .24)
            self.frutas.append(f)

    def cortar(self, f, angulo):
        f.muerta = True
        if f.bomba:
            self.vidas -= 1
            self.temblor = .45
            self.tocar("bomba")
            self.textos.append([f.x, f.y, "¡BOOM! −1 vida", (255, 80, 80), 1.2, False])
            colores = [(255, 226, 74), (255, 122, 26), (255, 58, 42), (85, 85, 85)]
            self.gotas += [Gota(f.x, f.y, random.choice(colores), self.K, 1.4) for _ in range(40)]
            if self.vidas <= 0:
                self.terminar()
            return
        self.tocar("corte")
        self.mitades += [Mitad(f, angulo, 1, self.K), Mitad(f, angulo, -1, self.K)]
        self.gotas += [Gota(f.x, f.y, f.jugo, self.K) for _ in range(18)]
        self.manchas.append(Mancha(f.x, f.y, f.r * random.uniform(1.1, 1.5), f.jugo, angulo))
        if self.pantalla != "juego":
            return
        ahora = time.perf_counter()
        self.combo = self.combo + 1 if ahora - self.ult_corte < .28 else 1
        self.ult_corte = ahora
        self.puntos += 1
        self.textos.append([f.x, f.y - f.r, "+1", interfaz.BLANCO, .7, False])
        if self.combo >= 3:
            self.puntos += self.combo
            self.mejor_combo = max(self.mejor_combo, self.combo)
            self.tocar("combo")
            self.textos.append([self.W / 2, self.H * .3, f"¡Combo x{self.combo}! +{self.combo}", interfaz.DORADO, 1.1, True])

    def terminar(self):
        if self.puntos > self.record:
            self.record = self.puntos
            guardar_record(self.record)
        self.tocar("fin")
        self.ir_a("fin")

    # ---------- dedo (cámara o mouse) ----------
    def mover(self, x, y):
        ahora = time.perf_counter()
        self.rastro.append((x, y, ahora))
        if len(self.rastro) < 2:
            return
        (ax, ay, at), (bx, by, bt) = self.rastro[-2], self.rastro[-1]
        dx, dy = bx - ax, by - ay
        largo = math.hypot(dx, dy)
        if largo < 4:
            return
        if largo / max(1e-3, bt - at) > 2600 * self.K and ahora - self.ult_espada > .25:
            self.ult_espada = ahora
            self.tocar("espada")
        angulo = math.atan2(dy, dx)
        objetivos = list(self.frutas)
        if self.boton_fruta:
            objetivos.append(self.boton_fruta)
        for f in objetivos:
            if f.muerta or getattr(f, "espera", 0) > 0:
                continue
            t = max(0, min(1, ((f.x - ax) * dx + (f.y - ay) * dy) / (largo * largo)))
            if math.hypot(ax + dx * t - f.x, ay + dy * t - f.y) < f.r * .9:
                self.cortar(f, angulo)
                if f is self.boton_fruta:
                    self.boton_fruta = None
                    self.ir_a("juego")
                    return

    # ---------- bucle ----------
    def paso(self, dt):
        self.t += dt
        if self.pantalla == "juego":
            self.tiempo -= dt
            seg = math.ceil(self.tiempo)
            if 0 < seg <= 5 and seg < self.ult_tic:
                self.tocar("tic")
            self.ult_tic = seg
            if self.tiempo <= 0:
                self.tiempo = 0
                self.terminar()
        self.prox_ola -= dt
        if self.prox_ola <= 0:
            self.ola()
            self.prox_ola = random.uniform(.9, 1.7) if self.pantalla == "juego" else random.uniform(1.4, 2.4)

        if self.camara:
            dedo = self.camara.leer()[0]
            self.objetivo = (dedo[0] * self.W, dedo[1] * self.H) if dedo else None
        if self.objetivo:
            if not self.dedo:
                self.dedo = list(self.objetivo)
                self.rastro = []
            k = 1 - math.exp(-dt * 80)
            self.dedo[0] += (self.objetivo[0] - self.dedo[0]) * k
            self.dedo[1] += (self.objetivo[1] - self.dedo[1]) * k
            self.mover(*self.dedo)
        elif self.dedo:
            self.dedo = None
            self.rastro = []
        self.botones.actualizar(self, self.dedo or (pygame.mouse.get_pos() if pygame.mouse.get_focused() else None))

        for f in self.frutas:
            if getattr(f, "espera", 0) > 0:
                f.espera -= dt
                continue
            f.mover(dt, self.G)
            if f.y > self.H + f.r * 2 and f.vy > 0:
                f.muerta = True
        self.frutas = [f for f in self.frutas if not f.muerta]
        for m in self.mitades:
            m.mover(dt, self.G)
        self.mitades = [m for m in self.mitades if m.y < self.H + m.r * 3]
        for g in self.gotas:
            g.mover(dt, self.G)
        self.gotas = [g for g in self.gotas if g.vida > 0]
        if self.boton_fruta:
            self.boton_fruta.rot += self.boton_fruta.vr * dt
            self.boton_fruta.y = self.H * .74 + math.sin(self.t * 2) * 8 * self.K

    def dibujar(self, dt):
        sup = self.sup
        ox = oy = 0
        if self.temblor > 0:
            self.temblor -= dt
            ox, oy = random.uniform(-8, 8) * self.K, random.uniform(-8, 8) * self.K
        self.fondo.dibujar_atras(sup, dt, self.t)
        self.fondo.dibujar_delante(sup, dt, self.t)
        for m in self.manchas:
            m.dibujar(sup, dt)
        self.manchas = [m for m in self.manchas if m.vida > 0]
        for f in self.frutas:
            if getattr(f, "espera", 0) <= 0:
                f.x, f.y = f.x + ox, f.y + oy
                f.dibujar(sup, self.t)
                f.x, f.y = f.x - ox, f.y - oy
        for m in self.mitades:
            m.dibujar(sup)
        for g in self.gotas:
            g.dibujar(sup)
        if self.pantalla == "juego":
            interfaz.paneles(self)
        else:
            interfaz.tarjeta(self)
            if self.boton_fruta:
                self.boton_fruta.dibujar(sup, self.t)
        for x in self.textos:
            x[4] -= dt
            x[1] -= 40 * dt
            if x[4] > 0:
                tam = (34 if x[5] else 22) * max(.8, self.K)
                gr.texto(sup, x[2], tam, x[3], (x[0], x[1]), borde=3, color_borde=(27, 27, 42))
        self.textos = [x for x in self.textos if x[4] > 0]
        interfaz.estela(self)
        interfaz.cuadro_camara(self)
        self.botones.dibujar(self)
        interfaz.cursor_dedo(self)

    def eventos(self):
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                return False
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    if self.pantalla == "juego":
                        self.ir_a("inicio")
                    else:
                        return False
                elif e.key == pygame.K_F11:
                    self.cambiar_pantalla_completa()
                elif e.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER) and self.pantalla != "juego":
                    self.ir_a("juego")
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                self.botones.clic(self, e.pos)
            elif e.type == pygame.MOUSEMOTION and not self.objetivo:
                self.mover(*e.pos)
        return True

    def correr(self, cuadros=None, al_cuadro=None):
        pantalla_siempre_encendida(True)
        try:
            self._bucle(cuadros, al_cuadro)
        finally:
            pantalla_siempre_encendida(False)
            self.apagar_camara()
            pygame.quit()

    def _bucle(self, cuadros, al_cuadro):
        n = 0
        seguir = True
        while seguir:
            dt = min(.033, self.reloj.tick(60) / 1000)
            seguir = self.eventos()
            if al_cuadro:
                al_cuadro(self, n)
            self.paso(dt)
            self.dibujar(dt)
            pygame.display.flip()
            n += 1
            if cuadros and n >= cuadros:
                break


if __name__ == "__main__":
    Juego(sin_camara="--sin-camara" in sys.argv,
          ventana=(1280, 720) if "--ventana" in sys.argv else None).correr()

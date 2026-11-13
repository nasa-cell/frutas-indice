"""Lo que se dibuja encima del juego: paneles, tarjetas, cuadro de la cámara,
estela de la espada y botones (pantalla completa y cámara)."""
import math
import time

import pygame

import graficos as gr

DORADO = (255, 216, 90)
CELESTE = (159, 184, 232)
BLANCO = (255, 255, 255)
ROJO = (255, 74, 90)
TEXTO_CLARO = (234, 242, 255)
DEDOS = [[0, 1, 2, 3, 4], [0, 5, 6, 7, 8], [5, 9, 10, 11, 12], [9, 13, 14, 15, 16], [13, 17, 18, 19, 20], [0, 17]]
ESPERA_BOTON = 1.0   # segundos con el dedo encima para activar un botón


def caja_camara(j):
    """Rectángulo del cuadro de la cámara (abajo a la derecha)."""
    cw = int(min(210 * j.s, j.W * .3))
    ch = int(cw * 9 / 16)
    m = int(12 * j.s)
    return pygame.Rect(j.W - m - cw, j.H - m - ch - int(22 * j.s), cw, ch)


# ---------- paneles del juego (diseño B) ----------
def paneles(j):
    s, sup = j.s, j.sup
    m = int(12 * s)
    w, h = int(150 * s), int(76 * s)
    sup.blit(gr.panel(w, h, int(18 * s)), (m, j.TOP))
    gr.texto(sup, "PUNTOS", 11 * s, CELESTE, (m + 16 * s, j.TOP + 17 * s), "midleft", "media")
    gr.texto(sup, f"récord {j.record}", 11 * s, CELESTE, (m + w - 14 * s, j.TOP + 17 * s), "midright", "media")
    gr.texto(sup, j.puntos, 36 * s, DORADO, (m + 16 * s, j.TOP + 49 * s), "midleft")
    if j.combo >= 2 and time.perf_counter() - j.ult_corte < 1.2:
        gr.texto(sup, f"x{j.combo}", 14 * s, (127, 216, 255), (m + w - 14 * s, j.TOP + 52 * s), "midright")
    r0 = 36 * s
    cx, cy = j.W - m - r0 - 6, j.TOP + r0 + 4
    p = max(0, j.tiempo / j.DURACION)
    rojo = j.tiempo < 10
    sup.blit(gr.panel(int(r0 * 2), int(r0 * 2), int(r0)), (cx - r0, cy - r0))
    gr.arco_grueso(sup, (60, 74, 110), (cx, cy), r0 - 9 * s, 0, math.tau, 7 * s)
    gr.arco_grueso(sup, ROJO if rojo else DORADO, (cx, cy), r0 - 9 * s, -math.pi / 2, -math.pi / 2 + math.tau * p, 7 * s)
    gr.texto(sup, math.ceil(j.tiempo), 22 * s, (255, 106, 106) if rojo else BLANCO, (cx, cy + 1))
    for i in range(j.VIDAS):
        img = j.corazones[0 if i < j.vidas else 1]
        sup.blit(img, img.get_rect(center=(cx + (i - 1) * 26 * s, cy + r0 + 18 * s)))


# ---------- tarjetas de inicio y fin ----------
def tarjeta(j):
    s, sup = j.s, j.sup
    w, h = int(min(520 * s, j.W - 32)), int(250 * s)
    x, y = (j.W - w) // 2, int(j.H * .1)
    sup.blit(gr.panel(w, h, int(26 * s)), (x, y))
    titulo = dict(borde=max(2, int(3 * s)), color_borde=(42, 22, 0), sombra=((184, 134, 11), int(5 * s)))
    if j.pantalla == "inicio":
        gr.texto(sup, "Corte Frutal", 54 * s, DORADO, (j.W / 2, y + 62 * s), **titulo)
        gr.texto(sup, "Levanta tu dedo índice frente a la cámara", 17 * s, TEXTO_CLARO, (j.W / 2, y + 128 * s), peso="media")
        gr.texto(sup, "y corta las frutas. No toques las bombas.", 17 * s, TEXTO_CLARO, (j.W / 2, y + 154 * s), peso="media")
        gr.texto(sup, f"Récord: {j.record}  ·  60 segundos  ·  3 vidas", 14 * s, CELESTE, (j.W / 2, y + 196 * s), peso="media")
        leyenda = "¡Corta esta fruta para jugar!"
    else:
        gr.texto(sup, "¡Se acabó!", 50 * s, DORADO, (j.W / 2, y + 58 * s), **titulo)
        gr.texto(sup, "Puntos", 16 * s, TEXTO_CLARO, (j.W / 2, y + 110 * s), peso="media")
        gr.texto(sup, j.puntos, 54 * s, BLANCO, (j.W / 2, y + 156 * s), sombra=((184, 134, 11), int(4 * s)))
        gr.texto(sup, f"Récord: {j.record}  ·  Mejor combo: {j.mejor_combo}", 14 * s, CELESTE, (j.W / 2, y + 212 * s), peso="media")
        leyenda = "Corta la fruta para jugar otra vez"
    if j.boton_fruta:
        f = j.boton_fruta
        gr.texto(sup, leyenda, 18 * s, DORADO, (f.x, f.y + f.r + 26 * s), borde=3, color_borde=(8, 20, 48))


# ---------- cuadro de la cámara ----------
def cuadro_camara(j):
    sup, s = j.sup, j.s
    caja = caja_camara(j)
    cx, cy, cw, ch = caja
    pygame.draw.rect(sup, (8, 14, 32), caja, border_radius=12)
    mano = zona = mini = None
    fps = 0
    if j.camara:
        _, mano, zona, mini, fps = j.camara.leer()
    if mini is not None:
        img = pygame.transform.smoothscale(pygame.surfarray.make_surface(mini.swapaxes(0, 1)), (cw, ch)).convert_alpha()
        mascara = pygame.Surface((cw, ch), pygame.SRCALPHA)
        pygame.draw.rect(mascara, (255, 255, 255, 255), (0, 0, cw, ch), border_radius=12)
        img.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        sup.blit(img, (cx, cy))
        if mano:
            pt = [(cx + (1 - x) * cw, cy + y * ch) for x, y in mano]
            for cadena in DEDOS:
                pygame.draw.lines(sup, (127, 216, 255), False, [pt[i] for i in cadena], 2)
            for i, p in enumerate(pt):
                pygame.draw.circle(sup, DORADO if i == 8 else BLANCO, p, 5 if i == 8 else 2)
            zx, zy, z = zona
            if z < .97:
                pygame.draw.rect(sup, DORADO, (cx + (1 - zx - z) * cw, cy + zy * ch, z * cw, z * ch), 1)
    else:
        gr.texto(sup, "cámara apagada" if not j.camara else "cámara", 13 * s, (200, 212, 240), caja.center, peso="media")
    pygame.draw.rect(sup, DORADO, caja, 2, border_radius=12)
    if not j.camara:
        estado, color = "cámara apagada · juegas con el mouse", (200, 212, 240)
    elif j.camara.estado != "lista":
        estado = j.camara.mensaje
        color = (255, 120, 120) if j.camara.estado == "error" else (255, 184, 74)
    elif mano:
        extra = f" · zoom x{1 / zona[2]:.1f}" if zona[2] < .97 else ""
        estado, color = f"mano detectada{extra} · {fps} fps", (60, 255, 122)
    else:
        estado, color = f"muestra tu mano · {fps} fps", (255, 184, 74)
    gr.texto(sup, "● " + estado, 11 * s, color, (cx + cw, cy + ch + 12 * s), "midright", "media")


# ---------- estela de la espada ----------
def estela(j):
    ahora = time.perf_counter()
    j.rastro = [p for p in j.rastro if ahora - p[2] < .16]
    n = len(j.rastro)
    if n < 2:
        return
    for color, ancho in (((120, 170, 230), 14), ((255, 255, 255), 5)):
        for i in range(1, n):
            k = i / n
            (ax, ay, _), (bx, by, _) = j.rastro[i - 1], j.rastro[i]
            w = max(1, int(ancho * k * max(.7, j.K)))
            c = tuple(int(v * (.45 + .55 * k)) for v in color)
            pygame.draw.line(j.sup, c, (ax, ay), (bx, by), w)
            pygame.draw.circle(j.sup, c, (bx, by), w / 2)


def cursor_dedo(j):
    if j.dedo:
        pygame.draw.circle(j.sup, DORADO, j.dedo, 14 * max(.8, j.K), 3)


# ---------- botones: pantalla completa y cámara ----------
def _icono_pantalla(sup, c, r, completa):
    x, y = c
    a, b = r * .42, r * .2
    color = DORADO
    for sx in (-1, 1):
        for sy in (-1, 1):
            if completa:   # flechas hacia adentro: salir de pantalla completa
                px, py = x + sx * b, y + sy * b
                pygame.draw.lines(sup, color, False, [(px, py + sy * (a - b)), (px, py), (px + sx * (a - b), py)], 3)
            else:          # esquinas hacia afuera: entrar a pantalla completa
                px, py = x + sx * a, y + sy * a
                pygame.draw.lines(sup, color, False, [(px, py - sy * (a - b)), (px, py), (px - sx * (a - b), py)], 3)


def _icono_camara(sup, c, r, encendida):
    x, y = c
    color = DORADO if encendida else CELESTE
    cuerpo = pygame.Rect(0, 0, r * .62, r * .46)
    cuerpo.center = (x - r * .1, y)
    pygame.draw.rect(sup, color, cuerpo, 3, border_radius=4)
    pygame.draw.polygon(sup, color, [(cuerpo.right, y - r * .06), (x + r * .42, y - r * .2), (x + r * .42, y + r * .2), (cuerpo.right, y + r * .06)])
    if not encendida:
        pygame.draw.line(sup, ROJO, (x - r * .45, y - r * .42), (x + r * .45, y + r * .42), 4)


class Botones:
    """Dos botones redondos encima del cuadro de la cámara.
    Se activan con clic o dejando el dedo (o el mouse) encima 1 segundo."""

    def __init__(self):
        self.encima = None      # nombre del botón que tiene el dedo encima
        self.desde = 0.0
        self.bloqueado = None   # recién activado: espera a que el dedo salga

    def lista(self, j):
        caja = caja_camara(j)
        r = int(24 * j.s)
        y = caja.top - r - int(10 * j.s)
        return [("camara", (caja.right - r, y), r), ("pantalla", (caja.right - r * 3 - int(10 * j.s), y), r)]

    def _bajo(self, j, pos):
        if pos is None:
            return None
        for nombre, c, r in self.lista(j):
            if math.hypot(pos[0] - c[0], pos[1] - c[1]) <= r * 1.15:
                return nombre
        return None

    def clic(self, j, pos):
        nombre = self._bajo(j, pos)
        if nombre:
            self.bloqueado = nombre
            j.accion_boton(nombre)
            return True
        return False

    def actualizar(self, j, puntero):
        nombre = self._bajo(j, puntero)
        if nombre != self.bloqueado:
            self.bloqueado = None if nombre is None else self.bloqueado
        if nombre is None or nombre == self.bloqueado:
            self.encima = None
            return
        ahora = time.perf_counter()
        if nombre != self.encima:
            self.encima, self.desde = nombre, ahora
        elif ahora - self.desde >= ESPERA_BOTON:
            self.encima = None
            self.bloqueado = nombre
            j.accion_boton(nombre)

    def dibujar(self, j):
        sup = j.sup
        ahora = time.perf_counter()
        for nombre, c, r in self.lista(j):
            grande = nombre == self.encima
            rr = int(r * (1.08 if grande else 1))
            sup.blit(gr.panel(rr * 2, rr * 2, rr), (c[0] - rr, c[1] - rr))
            if nombre == "pantalla":
                _icono_pantalla(sup, c, rr, j.completa)
            else:
                _icono_camara(sup, c, rr, j.camara is not None)
            if grande:
                p = min(1, (ahora - self.desde) / ESPERA_BOTON)
                gr.arco_grueso(sup, DORADO, c, rr + 5, -math.pi / 2, -math.pi / 2 + math.tau * p, 4)

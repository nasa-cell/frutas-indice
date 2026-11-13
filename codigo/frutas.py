"""Frutas, bombas, mitades cortadas, jugo y manchas."""
import json
import math
import random

import pygame


def color_hex(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


class Imagenes:
    """Carga los dibujos de las frutas (enteras y cortadas) y los escala con caché."""

    def __init__(self):
        with open("recursos/frutas/info.json", encoding="utf-8") as f:
            self.info = json.load(f)
        self.tipos = list(self.info)
        self.base = {}
        for tipo, d in self.info.items():
            for v in range(d["variantes"]):
                for s in range(3):
                    self.base[(tipo, v, s)] = (
                        pygame.image.load(f"recursos/frutas/{tipo}_{v}_{s}_entera.png").convert_alpha(),
                        pygame.image.load(f"recursos/frutas/{tipo}_{v}_{s}_corte.png").convert_alpha())
        self.bomba = pygame.image.load("recursos/frutas/bomba.png").convert_alpha()
        self._cache = {}

    def fruta(self, tipo, v, s, radio):
        """Las imágenes base están dibujadas con radio = r*2; se escalan al radio pedido."""
        clave = (tipo, v, s, int(radio))
        if clave not in self._cache:
            entera, corte = self.base[(tipo, v, s)]
            k = radio / (self.info[tipo]["r"] * 2)
            tam = lambda img: (max(2, int(img.get_width() * k)), max(2, int(img.get_height() * k)))
            self._cache[clave] = (pygame.transform.smoothscale(entera, tam(entera)),
                                  pygame.transform.smoothscale(corte, tam(corte)))
        return self._cache[clave]

    def bomba_de(self, radio):
        clave = ("bomba", int(radio))
        if clave not in self._cache:
            k = radio / 72
            self._cache[clave] = pygame.transform.smoothscale(
                self.bomba, (int(self.bomba.get_width() * k), int(self.bomba.get_height() * k)))
        return self._cache[clave]


class Fruta:
    def __init__(self, imagenes, x, y, vx, vy, escala, bomba=False):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.rot = random.uniform(0, 360)
        self.vr = random.uniform(-170, 170)
        self.bomba = bomba
        self.muerta = False
        if bomba:
            self.r = 36 * escala
            self.img = imagenes.bomba_de(self.r)
            self.vr = random.uniform(-110, 110)
        else:
            self.tipo = random.choice(imagenes.tipos)
            d = imagenes.info[self.tipo]
            self.variante = random.randrange(d["variantes"])
            self.semilla = random.randrange(3)
            self.r = d["r"] * escala * random.uniform(.85, 1.15)
            self.img, self.corte = imagenes.fruta(self.tipo, self.variante, self.semilla, self.r)
            self.jugo = color_hex(d["jugo"])

    def mover(self, dt, g):
        self.vy += g * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.rot += self.vr * dt

    def dibujar(self, sup, t):
        img = pygame.transform.rotozoom(self.img, self.rot, 1)
        sup.blit(img, img.get_rect(center=(self.x, self.y)))
        if self.bomba:  # chispa de la mecha
            ang = math.radians(-self.rot)
            mx = self.x + (math.cos(ang) * .42 - math.sin(ang) * -1.10) * self.r
            my = self.y + (math.sin(ang) * .42 + math.cos(ang) * -1.10) * self.r
            f = 1 + math.sin(t * 30) * .3
            for i in range(6):
                a = i / 6 * math.tau + t * 8
                col = (255, 226, 74) if i % 2 else (255, 122, 26)
                pygame.draw.line(sup, col, (mx, my), (mx + math.cos(a) * self.r * .25 * f, my + math.sin(a) * self.r * .25 * f), 2)


class Mitad:
    """Media fruta: la imagen del corte se gira para que la línea quede horizontal y se parte en dos."""

    def __init__(self, fruta, angulo, lado, escala):
        grados = math.degrees(angulo)
        girada = pygame.transform.rotozoom(fruta.corte, grados, 1)
        w, h = girada.get_size()
        if lado > 0:
            self.img = girada.subsurface((0, 0, w, h // 2)).copy()
            dy = -h / 4
        else:
            self.img = girada.subsurface((0, h // 2, w, h - h // 2)).copy()
            dy = h / 4
        self.base = -grados
        c, s = math.cos(angulo), math.sin(angulo)
        self.x = fruta.x - dy * s
        self.y = fruta.y + dy * c
        normal = angulo - math.pi / 2 if lado > 0 else angulo + math.pi / 2
        vel = random.uniform(70, 130) * escala
        self.vx = fruta.vx * .5 + math.cos(normal) * vel
        self.vy = min(fruta.vy * .3, 0) + math.sin(normal) * vel - 60 * escala
        self.giro = 0.0
        self.vg = random.uniform(80, 220) * lado
        self.r = fruta.r

    def mover(self, dt, g):
        self.vy += g * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.giro += self.vg * dt

    def dibujar(self, sup):
        img = pygame.transform.rotozoom(self.img, self.base + self.giro, 1)
        sup.blit(img, img.get_rect(center=(self.x, self.y)))


class Gota:
    def __init__(self, x, y, color, escala, fuerza=1.0):
        a = random.uniform(0, math.tau)
        v = random.uniform(80, 360) * escala * fuerza
        self.x, self.y = x, y
        self.vx, self.vy = math.cos(a) * v, math.sin(a) * v - 100 * escala
        self.r = random.uniform(2, 6) * escala
        self.color = color
        self.vida = random.uniform(.4, .9)

    def mover(self, dt, g):
        self.vy += g * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vida -= dt

    def dibujar(self, sup):
        if self.vida > 0:
            pygame.draw.circle(sup, self.color, (self.x, self.y), max(1, self.r * min(1, self.vida * 2)))


class Mancha:
    """Mancha de jugo que se desvanece en el fondo."""

    def __init__(self, x, y, r, color, angulo):
        tam = int(r * 4.2)
        base = pygame.Surface((tam, tam), pygame.SRCALPHA)
        c = tam / 2
        pygame.draw.ellipse(base, (*color, 255), (c - r * 1.1, c - r * .32, r * 2.2, r * .64))
        for _ in range(9):
            a = random.uniform(0, math.tau)
            d = r * random.uniform(.9, 1.8)
            pygame.draw.circle(base, (*color, 255), (c + math.cos(a) * d, c + math.sin(a) * d * .6), r * random.uniform(.06, .18))
        self.img = pygame.transform.rotate(base, -math.degrees(angulo))
        self.x, self.y = x, y
        self.vida = 2.5

    def dibujar(self, sup, dt):
        self.vida -= dt
        self.img.set_alpha(int(102 * min(1, self.vida / 1.2)))
        sup.blit(self.img, self.img.get_rect(center=(self.x, self.y)))

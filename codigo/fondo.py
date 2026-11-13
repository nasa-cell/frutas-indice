"""Fondo 1: bosque de noche con estrellas que titilan, estrellas fugaces,
halo de luna, niebla que se mueve y luciérnagas."""
import math
import random

import pygame

from graficos import elipse_suave, luz, resplandor


class Fondo:
    def __init__(self, ancho, alto):
        self.W, self.H = ancho, alto
        M = min(ancho, alto)
        self.cielo = pygame.transform.smoothscale(pygame.image.load("recursos/fondo/cielo.png").convert(), (ancho, alto))
        self.frente = pygame.transform.smoothscale(pygame.image.load("recursos/fondo/frente.png").convert_alpha(), (ancho, alto))
        rnd = random.Random(11)
        self.estrellas = [(rnd.random() * ancho, rnd.random() * alto * .72, rnd.random() * 1.4 + .6,
                           rnd.random() * math.tau, .8 + rnd.random() * 2.5) for _ in range(int(ancho * alto / 6500))]
        self.luna = (ancho * .8, alto * .2, M * .075)
        self.estrellas = [e for e in self.estrellas if math.hypot(e[0] - ancho * .8, e[1] - alto * .2) > M * .1]
        self.halo = resplandor(M * .075 * 2.9, (255, 240, 200), 95, 1.6)
        self.brillos = [luz(12, (215, 255, 140), (i + 1) / 8, 1.8) for i in range(8)]
        self.luciernagas = [[rnd.uniform(0, ancho), rnd.uniform(alto * .45, alto * .95), rnd.uniform(0, math.tau),
                             rnd.uniform(-14, 14), rnd.uniform(-8, 8)] for _ in range(32)]
        self.nieblas = []
        for i in range(6):
            w = rnd.uniform(ancho * .35, ancho * .7)
            self.nieblas.append([rnd.uniform(0, ancho), alto * (.7 + i * .045), w,
                                 rnd.uniform(8, 18) * (1 if i % 2 else -1), elipse_suave(w, w * .22, (170, 200, 255), 34)])
        self.fugaces = []
        self.prox_fugaz = 2.0

    def dibujar_atras(self, sup, dt, t):
        sup.blit(self.cielo, (0, 0))
        for x, y, r, f, v in self.estrellas:
            a = .35 + .65 * abs(math.sin(t * v + f))
            c = int(70 + 185 * a)
            pygame.draw.rect(sup, (c, c, c), (x - r / 2, y - r / 2, r, r))
            if r > 1.6:
                pygame.draw.line(sup, (c, c, c), (x - r * 1.6, y), (x + r * 1.6, y))
                pygame.draw.line(sup, (c, c, c), (x, y - r * 1.6), (x, y + r * 1.6))
        lx, ly, lr = self.luna
        self.halo.set_alpha(int(200 + 55 * math.sin(t * 1.3)))
        sup.blit(self.halo, self.halo.get_rect(center=(lx, ly)))

        self.prox_fugaz -= dt
        if self.prox_fugaz <= 0:
            self.prox_fugaz = random.uniform(2.5, 6)
            d = random.choice((-1, 1))
            self.fugaces.append([random.uniform(self.W * .15, self.W * .85), random.uniform(self.H * .03, self.H * .3),
                                 d * random.uniform(450, 750), random.uniform(150, 280), .8])
        for s in self.fugaces:
            s[0] += s[2] * dt
            s[1] += s[3] * dt
            s[4] -= dt
            vida = max(0.0, min(1, s[4] * 2))
            for k in range(8):
                a = (1 - k / 8) * vida
                c = int(255 * a)
                x1, y1 = s[0] - s[2] * .015 * k, s[1] - s[3] * .015 * k
                x2, y2 = s[0] - s[2] * .015 * (k + 1), s[1] - s[3] * .015 * (k + 1)
                pygame.draw.line(sup, (c, c, min(255, c + 20)), (x1, y1), (x2, y2), max(1, 3 - k // 3))
        self.fugaces = [s for s in self.fugaces if s[4] > 0]

    def dibujar_delante(self, sup, dt, t):
        sup.blit(self.frente, (0, 0))
        for n in self.nieblas:
            n[0] += n[3] * dt
            if n[0] > self.W + n[2]:
                n[0] = -n[2]
            if n[0] < -n[2]:
                n[0] = self.W + n[2]
            sup.blit(n[4], n[4].get_rect(center=(n[0], n[1])))
        for l in self.luciernagas:
            l[0] += (l[3] + math.cos(t * .7 + l[2]) * 18) * dt
            l[1] += (l[4] + math.sin(t * .9 + l[2]) * 14) * dt
            if l[0] < -10:
                l[0] = self.W + 10
            if l[0] > self.W + 10:
                l[0] = -10
            if (l[1] < self.H * .4 and l[4] < 0) or (l[1] > self.H and l[4] > 0):
                l[4] *= -1
            a = .25 + .75 * max(0, math.sin(t * 1.8 + l[2]))
            img = self.brillos[min(7, int(a * 8))]
            sup.blit(img, img.get_rect(center=(l[0], l[1])), special_flags=pygame.BLEND_ADD)

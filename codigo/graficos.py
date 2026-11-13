"""Utilidades de dibujo: degradados, brillos, textos con borde y paneles."""
import math
import numpy as np
import pygame

_cache_letras = {}
RUTA_LETRA = {
    "gruesa": "recursos/letra/MPLUSRounded1c-ExtraBold.ttf",
    "media": "recursos/letra/MPLUSRounded1c-Medium.ttf",
}


def letra(tam, peso="gruesa"):
    clave = (int(tam), peso)
    if clave not in _cache_letras:
        _cache_letras[clave] = pygame.font.Font(RUTA_LETRA[peso], max(8, int(tam)))
    return _cache_letras[clave]


def resplandor(radio, color, alfa_max=255, curva=2.0):
    """Círculo de luz que se desvanece hacia el borde."""
    tam = int(radio * 2) + 2
    sup = pygame.Surface((tam, tam), pygame.SRCALPHA)
    yy, xx = np.mgrid[0:tam, 0:tam]
    c = (tam - 1) / 2
    d = np.sqrt((xx - c) ** 2 + (yy - c) ** 2) / max(1, radio)
    a = np.clip(1 - d, 0, 1) ** curva * alfa_max
    sup.fill((*color, 0))
    pixeles = pygame.surfarray.pixels_alpha(sup)
    pixeles[:, :] = a.T.astype(np.uint8)
    del pixeles
    return sup


def luz(radio, color, intensidad=1.0, curva=2.0):
    """Luz para sumar con BLEND_ADD (el color ya va multiplicado por el brillo)."""
    tam = int(radio * 2) + 2
    yy, xx = np.mgrid[0:tam, 0:tam]
    c = (tam - 1) / 2
    d = np.sqrt((xx - c) ** 2 + (yy - c) ** 2) / max(1, radio)
    a = np.clip(1 - d, 0, 1) ** curva * intensidad
    rgb = np.stack([a * color[0], a * color[1], a * color[2]], axis=-1).clip(0, 255).astype(np.uint8)
    return pygame.surfarray.make_surface(rgb.transpose(1, 0, 2))


def elipse_suave(ancho, alto, color, alfa_max):
    sup = pygame.Surface((int(ancho), int(alto)), pygame.SRCALPHA)
    yy, xx = np.mgrid[0:int(alto), 0:int(ancho)]
    d = np.sqrt(((xx - ancho / 2) / (ancho / 2)) ** 2 + ((yy - alto / 2) / (alto / 2)) ** 2)
    a = np.clip(1 - d, 0, 1) ** 1.6 * alfa_max
    sup.fill((*color, 0))
    pixeles = pygame.surfarray.pixels_alpha(sup)
    pixeles[:, :] = a.T.astype(np.uint8)
    del pixeles
    return sup


def texto(sup, cadena, tam, color, pos, ancla="center", peso="gruesa", borde=0, color_borde=(8, 20, 48), sombra=None):
    """Escribe texto con borde opcional (como en la maqueta)."""
    f = letra(tam, peso)
    img = f.render(str(cadena), True, color)
    rect = img.get_rect(**{ancla: (int(pos[0]), int(pos[1]))})
    if sombra:
        s_img = f.render(str(cadena), True, sombra[0])
        for b in range(1, sombra[1] + 1):
            sup.blit(s_img, rect.move(0, b + borde))
    if borde:
        b_img = f.render(str(cadena), True, color_borde)
        for ang in range(0, 360, 30):
            dx = round(math.cos(math.radians(ang)) * borde)
            dy = round(math.sin(math.radians(ang)) * borde)
            sup.blit(b_img, rect.move(dx, dy))
    sup.blit(img, rect)
    return rect


_cache_paneles = {}


def panel(ancho, alto, radio, borde=(255, 216, 90)):
    """Panel azul noche con borde dorado y brillo arriba (diseño B)."""
    clave = (int(ancho), int(alto), int(radio))
    if clave in _cache_paneles:
        return _cache_paneles[clave]
    w, h, r = clave
    sup = pygame.Surface((w, h), pygame.SRCALPHA)
    for y in range(h):
        t = y / max(1, h - 1)
        col = (int(30 + (10 - 30) * t), int(52 + (20 - 52) * t), int(112 + (52 - 112) * t), 218)
        pygame.draw.line(sup, col, (0, y), (w, y))
    mascara = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(mascara, (255, 255, 255, 255), (0, 0, w, h), border_radius=r)
    sup.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    brillo = pygame.Surface((w - 8, int(h * .42)), pygame.SRCALPHA)
    pygame.draw.rect(brillo, (255, 255, 255, 18), brillo.get_rect(), border_radius=max(2, r - 4))
    sup.blit(brillo, (4, 3))
    pygame.draw.rect(sup, borde, (0, 0, w, h), width=2, border_radius=r)
    _cache_paneles[clave] = sup
    return sup


def corazon(tam, lleno):
    s = int(tam * 2.4)
    sup = pygame.Surface((s, s), pygame.SRCALPHA)
    cx, cy = s / 2, s / 2 + tam * .1

    def bezier(p0, p1, p2, p3, n=16):
        return [((1 - t) ** 3 * p0[0] + 3 * (1 - t) ** 2 * t * p1[0] + 3 * (1 - t) * t * t * p2[0] + t ** 3 * p3[0],
                 (1 - t) ** 3 * p0[1] + 3 * (1 - t) ** 2 * t * p1[1] + 3 * (1 - t) * t * t * p2[1] + t ** 3 * p3[1])
                for t in [i / n for i in range(n + 1)]]
    a = (cx, cy + tam * .35)
    puntos = bezier(a, (cx - tam, cy - tam * .3), (cx - tam * .45, cy - tam), (cx, cy - tam * .45))
    puntos += bezier((cx, cy - tam * .45), (cx + tam * .45, cy - tam), (cx + tam, cy - tam * .3), a)
    if lleno:
        pygame.draw.polygon(sup, (255, 74, 106), puntos)
        pygame.draw.polygon(sup, (122, 15, 42), puntos, 2)
        pygame.draw.ellipse(sup, (255, 255, 255, 205), (cx - tam * .48, cy - tam * .5, tam * .3, tam * .16))
    else:
        pygame.draw.polygon(sup, (120, 120, 140, 90), puntos)
        pygame.draw.polygon(sup, (80, 80, 100, 150), puntos, 2)
    return sup


def estrella(sup, cx, cy, r, color):
    puntos = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * .45
        puntos.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
    pygame.draw.polygon(sup, color, puntos)


def arco_grueso(sup, color, centro, radio, inicio, fin, grosor):
    """Arco con puntas redondas (pygame.draw.arc deja huecos)."""
    if fin <= inicio:
        return
    pasos = max(2, int((fin - inicio) * radio / 2))
    for i in range(pasos + 1):
        a = inicio + (fin - inicio) * i / pasos
        pygame.draw.circle(sup, color, (centro[0] + math.cos(a) * radio, centro[1] + math.sin(a) * radio), grosor / 2)

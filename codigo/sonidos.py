"""Sonidos hechos con código (sin archivos de internet)."""
import numpy as np
import pygame

FRECUENCIA = 44100


def _sonido(onda, volumen=.5):
    onda = np.clip(onda * volumen, -1, 1)
    datos = (onda * 32767).astype(np.int16)
    return pygame.sndarray.make_sound(np.ascontiguousarray(np.column_stack([datos, datos])))


def _t(segundos):
    return np.linspace(0, segundos, int(FRECUENCIA * segundos), endpoint=False)


def _paso_bajo(x, k):
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc += k * (v - acc)
        y[i] = acc
    return y


def crear():
    rng = np.random.default_rng(3)
    s = {}
    # corte: silbido corto + jugoso
    t = _t(.18)
    ruido = rng.uniform(-1, 1, t.size)
    agudo = np.diff(ruido, prepend=0) * np.exp(-t * 28)
    jugo = np.sin(2 * np.pi * (180 - 400 * t) * t) * np.exp(-t * 22) * .5
    s["corte"] = _sonido(agudo * .6 + jugo, .55)
    # espada al mover rápido
    t = _t(.16)
    env = np.sin(np.pi * t / .16) ** 2
    s["espada"] = _sonido(_paso_bajo(rng.uniform(-1, 1, t.size), .25) * env * 2.2, .25)
    # bomba
    t = _t(.7)
    boom = _paso_bajo(rng.uniform(-1, 1, t.size), .05) * 6 * np.exp(-t * 5)
    boom += np.sin(2 * np.pi * 55 * t) * np.exp(-t * 4) * .8
    s["bomba"] = _sonido(boom, .7)
    # combo: tres notas
    partes = []
    for f in (784, 988, 1319):
        t = _t(.09)
        partes.append((np.sin(2 * np.pi * f * t) + .3 * np.sin(4 * np.pi * f * t)) * np.exp(-t * 18))
    s["combo"] = _sonido(np.concatenate(partes), .35)
    # inicio y fin
    partes = []
    for f in (523, 659, 784, 1047):
        t = _t(.11)
        partes.append(np.sin(2 * np.pi * f * t) * np.exp(-t * 10))
    s["inicio"] = _sonido(np.concatenate(partes), .35)
    partes = []
    for f in (784, 659, 523, 392):
        t = _t(.16)
        partes.append(np.sin(2 * np.pi * f * t) * np.exp(-t * 7))
    s["fin"] = _sonido(np.concatenate(partes), .35)
    # tic de los últimos segundos
    t = _t(.05)
    s["tic"] = _sonido(np.sin(2 * np.pi * 1500 * t) * np.exp(-t * 60), .25)
    return s

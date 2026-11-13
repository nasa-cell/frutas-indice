"""Dibuja las pantallas del instalador (opción C) en BMP para Inno Setup.

Uso: entorno\\Scripts\\python.exe aplicacion\\crear_imagenes.py
"""
import os

from PIL import Image, ImageDraw, ImageFont

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
SALIDA = os.path.join(AQUI, "imagenes")
W, H = 520, 600
PANEL = (11, 22, 48)
DORADO = (242, 182, 50)
OSCURO = (34, 34, 34)
BOTON = (150, 486, 370, 540)
CERRAR = (200, 552, 320, 584)
BARRA = (40, 300, 480, 324)


def letra(tam, peso="ExtraBold"):
    return ImageFont.truetype(os.path.join(RAIZ, "recursos", "letra", f"MPLUSRounded1c-{peso}.ttf"), tam)


def fondo():
    cielo = Image.open(os.path.join(RAIZ, "recursos", "fondo", "cielo.png")).convert("RGB")
    esc = max(W / cielo.width, H / cielo.height)
    cielo = cielo.resize((round(cielo.width * esc), round(cielo.height * esc)), Image.LANCZOS)
    x = (cielo.width - W) // 2
    im = cielo.crop((x, 0, x + W, H))
    for i, nombre in enumerate(["sandia", "naranja", "fresa"]):
        fruta = Image.open(os.path.join(RAIZ, "recursos", "frutas", f"{nombre}_0_0_entera.png")).convert("RGBA")
        fruta.thumbnail((68, 68), Image.LANCZOS)
        im.paste(fruta, (W // 2 - 120 + i * 84 + (68 - fruta.width) // 2, 28 + (68 - fruta.height) // 2), fruta)
    return im


def titulo(d, texto, y, tam=44):
    d.text((W // 2, y), texto, font=letra(tam), fill="white", anchor="mm", stroke_width=4, stroke_fill="black")


def centro(d, texto, y, tam=15, color="white"):
    d.text((W // 2, y), texto, font=letra(tam, "Medium"), fill=color, anchor="mm", stroke_width=2, stroke_fill=(0, 0, 0))


def boton(d, caja, texto, relleno=DORADO, tinta=OSCURO, tam=24, borde=None):
    d.rounded_rectangle(caja, radius=12, fill=relleno, outline=borde, width=2 if borde else 0)
    d.text(((caja[0] + caja[2]) / 2, (caja[1] + caja[3]) / 2), texto, font=letra(tam), fill=tinta, anchor="mm")


def guardar(im, nombre, caja=None):
    (im.crop(caja) if caja else im).convert("RGB").save(os.path.join(SALIDA, nombre))


def main():
    os.makedirs(SALIDA, exist_ok=True)

    inicio = fondo()
    d = ImageDraw.Draw(inicio)
    titulo(d, "Corte Frutal", 128)
    centro(d, "Versión 1.0.0  ·  sin internet", 172)
    d.rounded_rectangle((24, 198, 496, 470), radius=14, fill=PANEL)
    boton(d, BOTON, "Instalar")
    centro(d, "Corta frutas con tu dedo índice frente a la cámara", 566, 13, (210, 222, 245))
    guardar(inicio, "inicio.bmp")
    guardar(inicio, "inicio_boton.bmp", BOTON)

    inst = fondo()
    d = ImageDraw.Draw(inst)
    titulo(d, "Instalando…", 160)
    centro(d, "Espera un momento, se copian los archivos del juego", 230, 14)
    capa = Image.new("RGBA", inst.size, (0, 0, 0, 0))
    ImageDraw.Draw(capa).rounded_rectangle(BARRA, radius=8, fill=(255, 255, 255, 60))
    inst = Image.alpha_composite(inst.convert("RGBA"), capa)
    guardar(inst, "instalando.bmp")
    barra = Image.new("RGB", (BARRA[2] - BARRA[0], BARRA[3] - BARRA[1]), DORADO)
    guardar(barra, "barra.bmp")

    listo = fondo()
    d = ImageDraw.Draw(listo)
    titulo(d, "¡Listo!", 160)
    centro(d, "Corte Frutal quedó instalado.", 230, 17)
    centro(d, "Tu récord se guarda en tu usuario y no se pierde al actualizar.", 262, 13, (210, 222, 245))
    corte = Image.open(os.path.join(RAIZ, "recursos", "frutas", "sandia_0_0_corte.png")).convert("RGBA")
    corte.thumbnail((170, 170), Image.LANCZOS)
    listo.paste(corte, ((W - corte.width) // 2, 375 - corte.height // 2), corte)
    boton(d, BOTON, "Jugar ahora")
    boton(d, CERRAR, "Cerrar", relleno=(20, 34, 70), tinta="white", tam=16, borde=(200, 210, 235))
    guardar(listo, "listo.bmp")
    guardar(listo, "listo_jugar.bmp", BOTON)
    guardar(listo, "listo_cerrar.bmp", CERRAR)
    print("Imágenes en", SALIDA)


if __name__ == "__main__":
    main()

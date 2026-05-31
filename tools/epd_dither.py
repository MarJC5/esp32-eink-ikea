#!/usr/bin/env python3
"""
epd_dither.py — conversion image -> plans 1bpp (noir / rouge) pour e-ink 3 couleurs.
Module partagé par img2cpp.py (génère images.h) et show.py (push série).

Fonctions clés :
  fit_image(img, w, h, mode)         -> image RGB w x h (cover/fit/stretch)
  text_image(text, w, h, ...)        -> image RGB avec du texte centré
  to_planes(img, dither, ...)        -> (black_mask, red_mask) listes 2D de bool
  pack_plane(mask)                   -> bytes 1bpp (MSB first, paddé à 8)

Modes de tramage :
  floyd3 : 3 couleurs N/B/R, diffusion d'erreur (rouge = ton intermédiaire) — le plus riche
  floyd  : N/B, Floyd-Steinberg (Pillow)
  ordered: N/B, Bayer 8x8
  none   : seuil dur
"""
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

BAYER8 = [
    [0, 32, 8, 40, 2, 34, 10, 42], [48, 16, 56, 24, 50, 18, 58, 26],
    [12, 44, 4, 36, 14, 46, 6, 38], [60, 28, 52, 20, 62, 30, 54, 22],
    [3, 35, 11, 43, 1, 33, 9, 41], [51, 19, 59, 27, 49, 17, 57, 25],
    [15, 47, 7, 39, 13, 45, 5, 37], [63, 31, 55, 23, 61, 29, 53, 21],
]

_FONT_PATHS = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/Library/Fonts/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "DejaVuSans.ttf",
]


def fit_image(img, w, h, mode="cover"):
    img = img.convert("RGB")
    if mode == "stretch":
        return img.resize((w, h))
    if mode == "cover":                       # remplit, recadrage centré
        s = max(w / img.width, h / img.height)
        nw, nh = max(1, round(img.width * s)), max(1, round(img.height * s))
        img = img.resize((nw, nh))
        x, y = (nw - w) // 2, (nh - h) // 2
        return img.crop((x, y, x + w, y + h))
    # fit (contain) + marges blanches
    im = img.copy()
    im.thumbnail((w, h))
    canvas = Image.new("RGB", (w, h), (255, 255, 255))
    canvas.paste(im, ((w - im.width) // 2, (h - im.height) // 2))
    return canvas


def place_image(src, w, h, zoom=1.0, off_x=0.0, off_y=0.0, bg=(255, 255, 255)):
    """Place `src` dans w x h avec zoom + décalage (repositionnement libre).
    zoom=1.0 = remplit (cover) ; <1 = marges blanches ; off_x/off_y dans [-1,1]
    (fraction d'un demi-écran) déplacent l'image. Recadre/centre, fond blanc."""
    src = src.convert("RGB")
    s = max(w / src.width, h / src.height) * max(0.05, zoom)   # base cover * zoom
    nw, nh = max(1, round(src.width * s)), max(1, round(src.height * s))
    big = src.resize((nw, nh))
    px = round((w - nw) / 2 + off_x * w / 2)
    py = round((h - nh) / 2 + off_y * h / 2)
    canvas = Image.new("RGB", (w, h), bg)
    canvas.paste(big, (px, py))
    return canvas


def _load_font(size):
    for p in _FONT_PATHS:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()


def text_image(text, w, h, color="black", bg="white", margin=8):
    """Rend `text` (lignes séparées par \\n) centré, taille auto pour remplir w x h."""
    img = Image.new("RGB", (w, h), bg)
    d = ImageDraw.Draw(img)
    lines = text.split("\n")
    size = h  # borne haute
    while size > 6:
        font = _load_font(size)
        widths, heights = [], []
        for ln in lines:
            box = d.textbbox((0, 0), ln or " ", font=font)
            widths.append(box[2] - box[0]); heights.append(box[3] - box[1])
        tw, th = (max(widths) if widths else 0), sum(heights) + (len(lines) - 1) * size // 5
        if tw <= w - 2 * margin and th <= h - 2 * margin:
            break
        size -= 2
    font = _load_font(size)
    th = 0
    line_h = []
    for ln in lines:
        box = d.textbbox((0, 0), ln or " ", font=font)
        lh = box[3] - box[1]; line_h.append((lh, box[1])); th += lh
    th += (len(lines) - 1) * size // 5
    y = (h - th) // 2
    for ln, (lh, top) in zip(lines, line_h):
        box = d.textbbox((0, 0), ln or " ", font=font)
        lw = box[2] - box[0]
        d.text(((w - lw) // 2 - box[0], y - top), ln, fill=color, font=font)
        y += lh + size // 5
    return img


def _red_mask(img, red_sat):
    px = img.load(); W, H = img.size
    m = [[False] * W for _ in range(H)]
    for y in range(H):
        for x in range(W):
            r, g, b = px[x, y]
            if (r - max(g, b)) >= red_sat and r > 100:
                m[y][x] = True
    return m


def to_planes(img, dither="floyd3", red_level=110, red_sat=90,
              brightness=1.0, invert=False, black_thr=128):
    """Renvoie (black_mask, red_mask) : listes 2D de bool (True = encre)."""
    W, H = img.size
    gray = img.convert("L")
    if brightness != 1.0:
        gray = ImageEnhance.Brightness(gray).enhance(brightness)
    if invert:
        gray = gray.point(lambda v: 255 - v)

    black = [[False] * W for _ in range(H)]

    if dither == "floyd3":
        # Diffusion d'erreur sur 3 tons : 0=noir, red_level=rouge, 255=blanc.
        red = [[False] * W for _ in range(H)]
        levels = [(0, "k"), (red_level, "r"), (255, "w")]
        buf = [[float(gray.getpixel((x, y))) for x in range(W)] for y in range(H)]
        for y in range(H):
            for x in range(W):
                old = buf[y][x]
                lv, ink = min(levels, key=lambda L: abs(L[0] - old))
                if ink == "k":
                    black[y][x] = True
                elif ink == "r":
                    red[y][x] = True
                err = old - lv
                if x + 1 < W:
                    buf[y][x + 1] += err * 7 / 16
                if y + 1 < H:
                    if x > 0:
                        buf[y + 1][x - 1] += err * 3 / 16
                    buf[y + 1][x] += err * 5 / 16
                    if x + 1 < W:
                        buf[y + 1][x + 1] += err * 1 / 16
        return black, red

    # Modes N/B (rouge = "vraie couleur" seulement)
    red = _red_mask(img, red_sat)
    gp = gray.load()
    for y in range(H):
        for x in range(W):
            if red[y][x]:
                gp[x, y] = 255
    if dither == "floyd":
        bw = gray.convert("1"); bp = bw.load()
        for y in range(H):
            for x in range(W):
                if not red[y][x] and bp[x, y] == 0:
                    black[y][x] = True
    elif dither == "ordered":
        for y in range(H):
            for x in range(W):
                if not red[y][x] and gp[x, y] < (BAYER8[y & 7][x & 7] + 0.5) * 255.0 / 64.0:
                    black[y][x] = True
    else:  # none
        for y in range(H):
            for x in range(W):
                if not red[y][x] and gp[x, y] < black_thr:
                    black[y][x] = True
    return black, red


def pack_plane(mask):
    """mask 2D bool -> (bytes 1bpp paddé à 8, w, h)."""
    h = len(mask)
    w = len(mask[0]) if h else 0
    row_bytes = (w + 7) // 8
    out = bytearray()
    for y in range(h):
        for bx in range(row_bytes):
            byte = 0
            for bit in range(8):
                x = bx * 8 + bit
                if x < w and mask[y][x]:
                    byte |= (0x80 >> bit)
            out.append(byte)
    return bytes(out), w, h

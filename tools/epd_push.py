#!/usr/bin/env python3
"""
epd_push.py — cœur partagé du PUSH série e-ink (utilisé par show.py CLI et epd_gui.py).

Rend une image/texte en 384x168 paysage, trame (epd_dither), envoie au firmware
(protocole "EPDF" + dims + plan noir + plan rouge), attend la fin du rendu.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image
import serial
from serial.tools import list_ports
import epd_dither as ed

SCREEN_W, SCREEN_H = 384, 168
DEFAULT_PORT = "/dev/cu.wchusbserial58FD0148761"


def list_ports_pref():
    """Ports série, ceux qui ressemblent à un ESP32 (USB-UART) d'abord."""
    devs = [p.device for p in list_ports.comports()]
    likely = ("usbserial", "wchusb", "slab", "usbmodem", "ttyusb", "ttyacm")
    pref = [d for d in devs if any(k in d.lower() for k in likely)]
    rest = [d for d in devs if d not in pref]
    return pref + rest


def default_port():
    ports = list_ports_pref()
    if DEFAULT_PORT in ports:
        return DEFAULT_PORT
    return ports[0] if ports else DEFAULT_PORT


def render_content(image_path=None, text=None, color="black", mode="cover",
                   zoom=1.0, off_x=0.0, off_y=0.0):
    """Image PIL 384x168 (paysage) depuis un fichier OU du texte.
    Pour une image : si zoom/off non par défaut -> placement libre (place_image),
    sinon cadrage classique (fit_image mode cover/fit/stretch)."""
    if text is not None:
        return ed.text_image(text.replace("\\n", "\n"), SCREEN_W, SCREEN_H, color=color)
    if not image_path:
        raise ValueError("Donne une image ou du texte.")
    src = Image.open(image_path)
    if zoom != 1.0 or off_x != 0.0 or off_y != 0.0:
        return ed.place_image(src, SCREEN_W, SCREEN_H, zoom, off_x, off_y)
    return ed.fit_image(src, SCREEN_W, SCREEN_H, mode)


def _masks(img, dither, red_level, brightness, invert):
    return ed.to_planes(img, dither=dither, red_level=red_level,
                        brightness=brightness, invert=invert)


def preview_rgb(img, dither="floyd3", red_level=110, brightness=1.0, invert=False):
    """Aperçu RGB 384x168 (blanc/noir/rouge) tel qu'il s'affichera."""
    black, red = _masks(img, dither, red_level, brightness, invert)
    out = Image.new("RGB", (SCREEN_W, SCREEN_H), (255, 255, 255))
    px = out.load()
    for y in range(SCREEN_H):
        for x in range(SCREEN_W):
            if red[y][x]:
                px[x, y] = (200, 30, 30)
            elif black[y][x]:
                px[x, y] = (0, 0, 0)
    return out


def make_frame(img, dither="floyd3", red_level=110, brightness=1.0, invert=False):
    """Trame + rotation vers le natif 168x384 + packing -> (bdata, rdata, w, h)."""
    native = img.transpose(Image.Transpose.ROTATE_270)   # 384x168 -> 168x384
    black, red = _masks(native, dither, red_level, brightness, invert)
    bdata, w, h = ed.pack_plane(black)
    rdata, _, _ = ed.pack_plane(red)
    return bdata, rdata, w, h


def push(port, bdata, rdata, w, h, log=print):
    """Reset l'ESP32, attend [PUSH] pret, envoie la trame, attend la fin du rendu."""
    s = serial.Serial(port, 115200, timeout=1)
    try:
        s.setDTR(False); s.setRTS(True); time.sleep(0.1)
        s.setRTS(False); time.sleep(0.1)
        t0 = time.time()
        while time.time() - t0 < 10:
            line = s.readline()
            if line and b"pret" in line:
                break
        s.reset_input_buffer()
        header = b"EPDF" + bytes([w & 0xFF, (w >> 8) & 0xFF, h & 0xFF, (h >> 8) & 0xFF])
        s.write(header + bdata + rdata)
        s.flush()
        log("envoyé, rendu en cours (~16 s)...")
        seen_rendu = False
        t0 = time.time()
        while time.time() - t0 < 35:
            line = s.readline()
            if not line:
                continue
            txt = line.decode(errors="replace").rstrip()
            if txt:
                log(txt)
            if "rendu" in txt:
                seen_rendu = True
            elif "pret" in txt and seen_rendu:
                break
        return seen_rendu
    finally:
        s.close()

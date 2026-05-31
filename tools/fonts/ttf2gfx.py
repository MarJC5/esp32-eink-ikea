#!/usr/bin/env python3
# =====================================================================
#  ttf2gfx — convertit une police TrueType (.ttf) en header au format
#  Adafruit GFX (GFXglyph[] + GFXfont + table de bitmaps PROGMEM).
#
#  Réimplémentation de fontconvert.c d'Adafruit (DPI 141, moteur
#  TrueType v35, packing de bits MSB d'abord, chaque glyphe padé à la
#  frontière d'octet). Produit des .h byte-pour-byte équivalents (mêmes
#  données numériques) à ceux livrés avec la lib Adafruit GFX.
#
#  Dépendance : freetype-py (cf. tools/requirements.txt).
#
#  Exemple :
#    python tools/fonts/ttf2gfx.py tools/fonts/FreeMonoBold.ttf 12 \
#        --name FreeMonoBold12pt -o include/fonts/FreeMonoBold12pt.h
# =====================================================================
import argparse
import ctypes
import os
import sys

import freetype

DPI = 141  # même résolution que fontconvert.c (≈ écran Adafruit 2.8")


def _force_interpreter_v35():
    """Force le moteur TrueType v35 (pas de hinting sous-pixel), comme
    fontconvert.c — sinon le rendu mono diffère de celui d'Adafruit."""
    fn = getattr(freetype, "FT_Property_Set", None)
    if fn is None:  # versions où ce n'est exposé que dans freetype.raw
        fn = getattr(getattr(freetype, "raw", None), "FT_Property_Set", None)
    if fn is None:
        sys.stderr.write("warn: FT_Property_Set indisponible, "
                         "rendu potentiellement non identique à Adafruit\n")
        return
    version = ctypes.c_uint(35)  # TT_INTERPRETER_VERSION_35
    fn(freetype.get_handle(), b"truetype", b"interpreter-version",
       ctypes.byref(version))


def build_font(ttf_path, size, first=0x20, last=0x7E):
    """Construit les données GFX d'une police.

    Retourne (bitmaps: bytes, glyphs: list[tuple], yadvance: int) où chaque
    glyphe est (bitmapOffset, width, height, xAdvance, xOffset, yOffset).
    Algorithme calqué sur fontconvert.c."""
    _force_interpreter_v35()
    face = freetype.Face(ttf_path)
    # 26.6 fixed-point : size << 6 ; résolution horizontale = DPI.
    face.set_char_size(size << 6, 0, DPI, 0)

    bitmaps = bytearray()
    glyphs = []
    bitmap_offset = 0

    # accumulateur de bits (équivalent de enbit() en C)
    acc = bytearray([0])  # acc[0] = octet courant
    bitpos = [0x80]       # masque du bit courant

    def enbit(value):
        if value:
            acc[0] |= bitpos[0]
        bitpos[0] >>= 1
        if bitpos[0] == 0:
            bitmaps.append(acc[0])
            acc[0] = 0
            bitpos[0] = 0x80

    for code in range(first, last + 1):
        face.load_char(chr(code),
                        freetype.FT_LOAD_RENDER | freetype.FT_LOAD_TARGET_MONO)
        g = face.glyph
        bmp = g.bitmap
        w, rows, pitch = bmp.width, bmp.rows, bmp.pitch
        buf = bmp.buffer
        top = g.bitmap_top

        # Glyphe à contour vide (espace, etc.) : les FreeType récents rendent
        # un bitmap 1x1 à pixel nul là où fontconvert obtenait 0x0. On
        # normalise en 0x0 pour rester identique aux polices Adafruit.
        if g.outline.n_contours == 0:
            w, rows, top = 0, 0, 0

        glyphs.append((
            bitmap_offset,
            w,
            rows,
            g.advance.x >> 6,   # xAdvance
            g.bitmap_left,      # xOffset
            1 - top,            # yOffset
        ))

        for y in range(rows):
            for x in range(w):
                byte = buf[y * pitch + (x >> 3)]
                enbit(byte & (0x80 >> (x & 7)))

        # pad de fin de glyphe jusqu'à la frontière d'octet
        n = (w * rows) & 7
        if n:
            for _ in range(8 - n):
                enbit(0)
        bitmap_offset += (w * rows + 7) // 8

    # yAdvance : hauteur de ligne ; fallback sur la hauteur du 1er glyphe
    metrics_height = face.size.height >> 6
    yadvance = metrics_height if metrics_height else (glyphs[0][2] if glyphs else 0)

    return bytes(bitmaps), glyphs, yadvance


def render_header(name, bitmaps, glyphs, yadvance, first, last):
    """Sérialise les données en header C (format Adafruit GFX)."""
    bits8 = last > 127
    out = []
    out.append("#pragma once")
    out.append("#include <Adafruit_GFX.h>")
    out.append("")
    out.append("// Généré par tools/ttf2gfx.py — NE PAS éditer à la main.")
    out.append("")

    # --- table de bitmaps ---
    out.append(f"const uint8_t {name}Bitmaps[] PROGMEM = {{")
    for i in range(0, len(bitmaps), 12):
        row = ", ".join(f"0x{b:02X}" for b in bitmaps[i:i + 12])
        out.append(f"  {row},")
    if out[-1].endswith(","):
        out[-1] = out[-1][:-1]  # retire la virgule finale
    out.append("};")
    out.append("")

    # --- table des glyphes ---
    out.append(f"const GFXglyph {name}Glyphs[] PROGMEM = {{")
    for idx, (off, w, h, xadv, xoff, yoff) in enumerate(glyphs):
        code = first + idx
        last_one = idx == len(glyphs) - 1
        comma = "" if last_one else ","
        ch = chr(code) if 0x20 <= code <= 0x7E else ""
        label = f" '{ch}'" if ch and ch != " " else (" ' '" if code == 0x20 else "")
        out.append(
            f"  {{ {off:5d}, {w:3d}, {h:3d}, {xadv:3d}, {xoff:4d}, {yoff:4d} }}{comma}"
            f"  // 0x{code:02X}{label}"
        )
    out.append("};")
    out.append("")

    # --- struct GFXfont ---
    out.append(f"const GFXfont {name} PROGMEM = {{")
    out.append(f"  (uint8_t  *){name}Bitmaps,")
    out.append(f"  (GFXglyph *){name}Glyphs,")
    out.append(f"  0x{first:02X}, 0x{last:02X}, {yadvance} }};")
    out.append("")
    approx = len(bitmaps) + (last - first + 1) * 7 + 7
    out.append(f"// Approx. {approx} bytes ({'8' if bits8 else '7'}-bit)")
    out.append("")
    return "\n".join(out)


def parse_int(s):
    return int(s, 0)  # gère 0x.. et décimal


def main():
    ap = argparse.ArgumentParser(description="TTF -> Adafruit GFX font header")
    ap.add_argument("ttf", help="fichier .ttf source")
    ap.add_argument("size", type=int, help="taille en points")
    ap.add_argument("--name", help="nom du symbole GFXfont "
                                    "(défaut: <base><size>pt<7|8>b)")
    ap.add_argument("--first", type=parse_int, default=0x20,
                    help="premier code (défaut 0x20)")
    ap.add_argument("--last", type=parse_int, default=0x7E,
                    help="dernier code (défaut 0x7E)")
    ap.add_argument("-o", "--output", help="fichier de sortie (défaut: stdout)")
    args = ap.parse_args()

    first, last = args.first, args.last
    if last < first:
        first, last = last, first

    name = args.name
    if not name:
        base = os.path.splitext(os.path.basename(args.ttf))[0]
        base = "".join(c if c.isalnum() else "_" for c in base)
        name = f"{base}{args.size}pt{'8' if last > 127 else '7'}b"

    bitmaps, glyphs, yadvance = build_font(args.ttf, args.size, first, last)
    header = render_header(name, bitmaps, glyphs, yadvance, first, last)

    if args.output:
        with open(args.output, "w") as f:
            f.write(header)
        sys.stderr.write(f"écrit {args.output} ({len(bitmaps)} octets bitmap, "
                         f"{len(glyphs)} glyphes, yAdvance={yadvance})\n")
    else:
        sys.stdout.write(header)


if __name__ == "__main__":
    main()

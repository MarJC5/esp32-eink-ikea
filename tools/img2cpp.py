#!/usr/bin/env python3
"""
img2cpp.py — Convertit une image en bitmaps C pour l'écran e-ink 3 couleurs
(noir / blanc / rouge), format GxEPD2 (1 bit/pixel, MSB first, largeur paddée à 8).

Génère/écrase include/images.h avec <NOM>_black[], <NOM>_red[], <NOM>_W/H.

Usage :
    python tools/img2cpp.py photo.png                 # défaut : 384x168, tramage floyd3 (N/B/R)
    python tools/img2cpp.py logo.png --dither floyd   # N/B seulement
    python tools/img2cpp.py img.png --mode cover --red-level 120 --brightness 1.1
    python tools/img2cpp.py logo.png --append         # ajoute sans écraser

Dépendance : pip install pillow
"""
import argparse
import os
import sys

try:
    from PIL import Image
    import epd_dither as ed
except ImportError as e:
    sys.exit(f"Dépendance manquante ({e}). pip install pillow ; epd_dither.py doit être à côté.")

# permet d'importer epd_dither même lancé depuis ailleurs
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HERE = os.path.dirname(os.path.abspath(__file__))
IMAGES_H = os.path.normpath(os.path.join(HERE, "..", "include", "images.h"))

HEADER = """#pragma once
// =====================================================================
//  images.h — bitmaps generes par tools/img2cpp.py  (NE PAS editer a la main)
//  Dalle 3 couleurs : un plan <nom>_black + un plan <nom>_red.
// =====================================================================
"""


def fmt_array(name, data):
    lines = [f"const unsigned char {name}[] = {{"]
    for i in range(0, len(data), 16):
        chunk = ", ".join(f"0x{b:02X}" for b in data[i:i + 16])
        lines.append(f"  {chunk},")
    lines.append("};")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="Image -> bitmaps C (e-ink 3 couleurs)")
    ap.add_argument("image", help="fichier image (png/jpg/...)")
    ap.add_argument("--name", help="nom de base des tableaux (def: nom du fichier)")
    ap.add_argument("--width", type=int, default=384, help="largeur cible (def 384)")
    ap.add_argument("--height", type=int, default=168, help="hauteur cible (def 168)")
    ap.add_argument("--dither", choices=["floyd3", "floyd", "ordered", "none"], default="floyd3",
                    help="tramage : floyd3 (N/B/R, def), floyd (N/B), ordered (Bayer), none (seuil)")
    ap.add_argument("--mode", choices=["cover", "fit", "stretch"], default="fit",
                    help="cadrage : fit (def, marges), cover (remplit+recadre), stretch (étire)")
    ap.add_argument("--red-level", type=int, default=110,
                    help="niveau de luminosité du rouge sur l'échelle 0-255 (floyd3 ; def 110)")
    ap.add_argument("--black-thr", type=int, default=128, help="seuil noir (mode none ; def 128)")
    ap.add_argument("--brightness", type=float, default=1.0, help="gain luminosité avant tramage")
    ap.add_argument("--invert", action="store_true", help="inverser noir/blanc")
    ap.add_argument("--red-sat", type=int, default=90, help="seuil de rougeur (modes N/B)")
    ap.add_argument("--no-fit", action="store_true", help="(alias de --mode stretch)")
    ap.add_argument("--append", action="store_true", help="ajouter au fichier existant")
    args = ap.parse_args()

    name = args.name or os.path.splitext(os.path.basename(args.image))[0]
    name = "".join(c if c.isalnum() else "_" for c in name).upper()

    mode = "stretch" if args.no_fit else args.mode
    img = ed.fit_image(Image.open(args.image), args.width, args.height, mode)
    black, red = ed.to_planes(img, dither=args.dither, red_level=args.red_level,
                              red_sat=args.red_sat, brightness=args.brightness,
                              invert=args.invert, black_thr=args.black_thr)
    bdata, w, h = ed.pack_plane(black)
    rdata, _, _ = ed.pack_plane(red)

    body = "\n".join([
        f"\n#define {name}_W {w}", f"#define {name}_H {h}",
        fmt_array(f"{name}_black", bdata), fmt_array(f"{name}_red", rdata), "",
    ])
    mode_w = "a" if (args.append and os.path.exists(IMAGES_H)) else "w"
    with open(IMAGES_H, mode_w) as f:
        f.write((HEADER if mode_w == "w" else "") + body)

    n_black = sum(sum(r) for r in black)
    n_red = sum(sum(r) for r in red)
    print(f"OK -> {IMAGES_H}")
    print(f"  {name} : {w}x{h} ({args.dither}) | noir={n_black} px, rouge={n_red} px")
    print(f"  Dans drawContent() :")
    print(f"    drawImageBW(0, 0, {name}_black, {name}_W, {name}_H);")
    if n_red:
        print(f"    drawImageRed(0, 0, {name}_red, {name}_W, {name}_H);")


if __name__ == "__main__":
    main()

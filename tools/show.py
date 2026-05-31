#!/usr/bin/env python3
"""
show.py — Affiche dynamiquement une image ou du texte sur l'e-ink via PUSH SÉRIE.
Aucun recompile/reflash : le firmware (qui écoute "EPDF") reçoit et affiche.

Usage :
    python tools/show.py photo.png
    python tools/show.py photo.png --mode cover --dither floyd3 --red-level 120
    python tools/show.py --text "Bonjour\\nFabrice"
    python tools/show.py --text "PROMO -50%" --color red

Dépendances : pip install pillow pyserial ; epd_dither.py à côté.
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from PIL import Image
    import serial
    import epd_dither as ed
except ImportError as e:
    sys.exit(f"Dépendance manquante ({e}). pip install pillow pyserial")

PORT = "/dev/cu.wchusbserial58FD0148761"
SCREEN_W, SCREEN_H = 384, 168          # paysage (vision utilisateur)


def build_landscape(args):
    if args.text is not None:
        return ed.text_image(args.text.replace("\\n", "\n"), SCREEN_W, SCREEN_H,
                             color=args.color)
    if not args.image:
        sys.exit("Donne une image ou --text.")
    mode = "stretch" if args.no_fit else args.mode
    return ed.fit_image(Image.open(args.image), SCREEN_W, SCREEN_H, mode)


def main():
    ap = argparse.ArgumentParser(description="Push série d'une image/texte vers l'e-ink")
    ap.add_argument("image", nargs="?", help="fichier image (sinon --text)")
    ap.add_argument("--text", help="afficher du texte (\\n = nouvelle ligne)")
    ap.add_argument("--color", choices=["black", "red"], default="black", help="couleur du texte")
    ap.add_argument("--dither", choices=["floyd3", "floyd", "ordered", "none"],
                    help="tramage (def: floyd3 pour image, none pour texte)")
    ap.add_argument("--mode", choices=["cover", "fit", "stretch"], default="cover")
    ap.add_argument("--red-level", type=int, default=110)
    ap.add_argument("--brightness", type=float, default=1.0)
    ap.add_argument("--invert", action="store_true")
    ap.add_argument("--no-fit", action="store_true")
    ap.add_argument("--port", default=PORT)
    ap.add_argument("--reset", action="store_true",
                    help="reset l'ESP32 à l'ouverture (sinon on garde le firmware en cours)")
    args = ap.parse_args()

    dither = args.dither or ("none" if args.text is not None else "floyd3")

    # 1) image paysage 384x168 (vision utilisateur)
    img = build_landscape(args)
    # 2) rotation vers le NATIF 168x384 (orientation du buffer matériel)
    native = img.transpose(Image.Transpose.ROTATE_270)   # 384x168 -> 168x384
    # 3) tramage + packing
    black, red = ed.to_planes(native, dither=dither, red_level=args.red_level,
                              brightness=args.brightness, invert=args.invert)
    bdata, w, h = ed.pack_plane(black)
    rdata, _, _ = ed.pack_plane(red)
    print(f"image {SCREEN_W}x{SCREEN_H} -> natif {w}x{h} ({dither}), {len(bdata)} o/plan")

    # 4) envoi série. On RESET proprement l'ESP32 (DTR/RTS) puis on attend
    #    "[PUSH] pret" : garantit que le firmware écoute avant l'envoi.
    s = serial.Serial(args.port, 115200, timeout=1)
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
    print("envoyé, rendu en cours (~16 s)...")

    # IMPORTANT : attendre la FIN du rendu (le "pret" qui suit "rendu") avant de
    # fermer — sinon close() reset l'ESP32 et coupe le refresh.
    seen_rendu = False
    t0 = time.time()
    while time.time() - t0 < 35:
        line = s.readline()
        if not line:
            continue
        txt = line.decode(errors="replace").rstrip()
        if txt:
            print("  ", txt)
        if "rendu" in txt:
            seen_rendu = True
        elif "pret" in txt and seen_rendu:
            break
    s.close()
    print("OK." if seen_rendu else "Terminé (pas de confirmation de rendu).")


if __name__ == "__main__":
    main()

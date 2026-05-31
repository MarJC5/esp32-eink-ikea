#!/usr/bin/env python3
"""
show.py — Affiche dynamiquement une image ou du texte sur l'e-ink via PUSH SÉRIE.
Aucun recompile/reflash : le firmware (qui écoute "EPDF") reçoit et affiche.

Usage :
    python tools/show.py photo.png
    python tools/show.py photo.png --mode cover --dither floyd3 --red-level 120
    python tools/show.py --text "Bonjour\\nFabrice"
    python tools/show.py --text "PROMO -50%" --color red

GUI équivalente : python tools/epd_gui.py  (ou make gui)
Dépendances : pip install pillow pyserial ; epd_dither.py + epd_push.py à côté.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import epd_push as ep
except ImportError as e:
    sys.exit(f"Dépendance manquante ({e}). pip install pillow pyserial")


def main():
    ap = argparse.ArgumentParser(description="Push série d'une image/texte vers l'e-ink")
    ap.add_argument("image", nargs="?", help="fichier image (sinon --text)")
    ap.add_argument("--text", help="afficher du texte (\\n = nouvelle ligne)")
    ap.add_argument("--color", choices=["black", "red"], default="black", help="couleur du texte")
    ap.add_argument("--dither", choices=["floyd3", "floyd", "ordered", "none"],
                    help="tramage (def: floyd3 pour image, none pour texte)")
    ap.add_argument("--mode", choices=["cover", "fit", "stretch"], default="cover")
    ap.add_argument("--zoom", type=float, default=1.0, help="zoom image (1.0 = remplit)")
    ap.add_argument("--off-x", type=float, default=0.0, help="décalage horizontal [-1..1]")
    ap.add_argument("--off-y", type=float, default=0.0, help="décalage vertical [-1..1]")
    ap.add_argument("--red-level", type=int, default=110)
    ap.add_argument("--brightness", type=float, default=1.0)
    ap.add_argument("--invert", action="store_true")
    ap.add_argument("--port", default=ep.default_port())
    args = ap.parse_args()

    dither = args.dither or ("none" if args.text is not None else "floyd3")
    img = ep.render_content(image_path=args.image, text=args.text,
                            color=args.color, mode=args.mode,
                            zoom=args.zoom, off_x=args.off_x, off_y=args.off_y)
    bdata, rdata, w, h = ep.make_frame(img, dither=dither, red_level=args.red_level,
                                       brightness=args.brightness, invert=args.invert)
    print(f"{ep.SCREEN_W}x{ep.SCREEN_H} -> natif {w}x{h} ({dither}), {len(bdata)} o/plan")
    ok = ep.push(args.port, bdata, rdata, w, h, log=lambda m: print("  ", m))
    print("OK." if ok else "Terminé (pas de confirmation de rendu).")


if __name__ == "__main__":
    main()

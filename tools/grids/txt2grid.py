#!/usr/bin/env python3
"""
txt2grid.py — Convertit/valide des fichiers ASCII de chiffres 0-9 en tableaux
C embarqués (include/grids.h) pour le module `grid` de l'ESP32, et CONTRÔLE
que les dimensions de chaque grille sont compatibles avec l'écran.

Format d'entrée : chiffres 0-9 séparés par des espaces, une ligne = une rangée.
Toutes les rangées doivent avoir le même nombre de colonnes.

Contrôles effectués (parser + checker) :
  - jetons : uniquement des chiffres 0-9 ;
  - rangées : toutes de même largeur (grille rectangulaire) ;
  - dimensions : la grille tient sur l'écran (par défaut 384x168) ;
    rapport d'ajustement (taille de cellule auto, pixels rendus, marges).

Usage :
    python tools/txt2grid.py data/grids/*.txt              # contrôle + génère grids.h
    python tools/txt2grid.py --check data/grids/*.txt      # contrôle seul (n'écrit rien)
    python tools/txt2grid.py --screen 384x168 --cell 8 ... # vérifie pour une cellule fixe
    python tools/txt2grid.py --strict ...                  # avertissements => erreurs
"""
import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GRIDS_H = os.path.normpath(os.path.join(HERE, "..", "include", "grids.h"))

DEFAULT_SCREEN = (384, 168)   # dalle e-ink en paysage (drawDigitGridFill etire de toute facon)

HEADER = """#pragma once
// =====================================================================
//  grids.h — grilles de chiffres generees par tools/txt2grid.py
//  NE PAS editer a la main. Regenerer avec : make grids
//  Chaque chiffre 0-9 = densite de remplissage (0=vide ... 9=plein).
// =====================================================================
#include <Arduino.h>
#include <pgmspace.h>
"""


class GridError(Exception):
    """Erreur bloquante de parsing/validation d'une grille."""


def slug(path):
    base = os.path.splitext(os.path.basename(path))[0]
    s = re.sub(r"[^0-9A-Za-z]", "_", base).upper()
    return "GRID_" + s


def parse(path):
    """Lit et valide un .txt. Retourne (rows, cols, nrows) ou lève GridError."""
    if not os.path.isfile(path):
        raise GridError(f"{path}: fichier introuvable")
    rows = []
    with open(path) as f:
        for ln, line in enumerate(f, 1):
            toks = line.split()
            if not toks:
                continue  # ignore lignes vides
            vals = []
            for t in toks:
                if not (len(t) == 1 and t.isdigit()):
                    raise GridError(
                        f"{path}:{ln}: jeton invalide {t!r} (attendu un chiffre 0-9)")
                vals.append(int(t))
            rows.append(vals)
    if not rows:
        raise GridError(f"{path}: aucune donnee")
    cols = len(rows[0])
    for i, r in enumerate(rows):
        if len(r) != cols:
            raise GridError(
                f"{path}: rangee {i+1} a {len(r)} colonnes, attendu {cols} "
                f"(toutes les rangees doivent etre de meme largeur)")
    return rows, cols, len(rows)


def check_fit(cols, rows, screen, cell):
    """Vérifie que la grille tient sur l'écran.
    Retourne (errors, warnings, info_lines). 'cell' = px/cellule fixe ou None (auto)."""
    sw, sh = screen
    errors, warnings, info = [], [], []

    if cell:
        cw = ch = cell
        rw, rh = cols * cw, rows * ch
        info.append(f"cellule fixe = {cell}px -> rendu {rw}x{rh}px (ecran {sw}x{sh})")
        if rw > sw or rh > sh:
            errors.append(
                f"deborde l'ecran : {rw}x{rh}px > {sw}x{sh}px "
                f"(reduis --cell, ou la grille a max {sw//cell}x{sh//cell} cellules)")
    else:
        # Auto-fit comme le firmware : cellPx = min(sw//cols, sh//rows).
        cpx = min(sw // cols if cols else 0, sh // rows if rows else 0)
        if cpx < 1:
            errors.append(
                f"trop de cellules pour l'ecran {sw}x{sh} : {cols}x{rows} "
                f"(max {sw}x{sh} cellules a 1px). Reduis la grille.")
            return errors, warnings, info
        rw, rh = cols * cpx, rows * cpx
        info.append(f"auto-fit -> cellule {cpx}px, rendu {rw}x{rh}px (ecran {sw}x{sh})")
        mx, my = sw - rw, sh - rh
        if mx == 0 and my == 0:
            info.append("remplit l'ecran exactement (aucune marge)")
        else:
            warnings.append(
                f"ne remplit pas l'ecran : marge {mx}px a droite, {my}px en bas. "
                f"Pour un remplissage exact, choisis une cellule qui divise {sw} ET {sh} "
                f"et la grille correspondante, ex. cell=8 -> {sw//8}x{sh//8}.")

    if cols > sw:
        errors.append(f"{cols} colonnes > largeur ecran {sw}px")
    if rows > sh:
        errors.append(f"{rows} rangees > hauteur ecran {sh}px")
    return errors, warnings, info


def emit(name, rows, cols, nrows):
    out = [f"\n#define {name}_COLS {cols}", f"#define {name}_ROWS {nrows}",
           f"const uint8_t {name}[] PROGMEM = {{"]
    for r in rows:
        out.append("  " + ", ".join(str(v) for v in r) + ",")
    out.append("};")
    return "\n".join(out)


def parse_screen(s):
    m = re.fullmatch(r"(\d+)x(\d+)", s.strip().lower())
    if not m:
        sys.exit(f"--screen invalide : {s!r} (format attendu LxH, ex. 384x168)")
    return int(m.group(1)), int(m.group(2))


def main():
    ap = argparse.ArgumentParser(description="Convertit/valide des grilles ASCII 0-9")
    ap.add_argument("files", nargs="+", help="fichiers .txt")
    ap.add_argument("--screen", type=parse_screen, default=DEFAULT_SCREEN,
                    metavar="LxH", help="dimensions ecran (def 384x168)")
    ap.add_argument("--cell", type=int, default=0,
                    help="taille de cellule fixe en px (def 0 = auto-fit)")
    ap.add_argument("--check", action="store_true",
                    help="contrôle seul, n'écrit pas grids.h")
    ap.add_argument("--strict", action="store_true",
                    help="traite les avertissements comme des erreurs")
    args = ap.parse_args()

    cell = args.cell if args.cell > 0 else None
    blocks, seen = [], {}
    n_err = n_warn = 0

    for path in args.files:
        name = slug(path)
        if name in seen:
            print(f"  [ERREUR] {name}: conflit de nom (deja {seen[name]})")
            n_err += 1
            continue
        seen[name] = path
        try:
            rows, cols, nrows = parse(path)
        except GridError as e:
            print(f"  [ERREUR] {e}")
            n_err += 1
            continue

        errors, warnings, info = check_fit(cols, nrows, args.screen, cell)
        status = "ERREUR" if errors else ("AVERT" if warnings else "OK")
        print(f"  [{status}] {name} : {cols}x{nrows}  <- {path}")
        for line in info:
            print(f"          {line}")
        for w in warnings:
            print(f"          ! {w}")
        for e in errors:
            print(f"          x {e}")
        n_err += len(errors)
        n_warn += len(warnings)
        if not errors:
            blocks.append(emit(name, rows, cols, nrows))

    if n_err or (args.strict and n_warn):
        print(f"ECHEC : {n_err} erreur(s), {n_warn} avertissement(s)"
              + (" (strict)" if args.strict and n_warn else ""))
        sys.exit(1)

    if args.check:
        print(f"CONTROLE OK : {len(args.files)} grille(s), {n_warn} avertissement(s)")
        return

    with open(GRIDS_H, "w") as f:
        f.write(HEADER + "\n".join(blocks) + "\n")
    print(f"OK -> {GRIDS_H}  ({len(blocks)} grille(s), {n_warn} avertissement(s))")


if __name__ == "__main__":
    main()

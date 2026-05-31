#!/usr/bin/env bash
# =====================================================================
#  gen_fonts.sh — régénère toutes les polices locales (include/fonts/*.h)
#  à partir des TTF source (tools/fonts/*.ttf) via ttf2gfx.py (même dossier).
#
#  Prérequis :
#    python -m venv .venv && source .venv/bin/activate
#    pip install -r tools/requirements.txt
#
#  Usage : ./tools/fonts/gen_fonts.sh   (ou : make fonts)
#  (PYTHON=python3.12 ./tools/fonts/gen_fonts.sh pour forcer un interpréteur)
# =====================================================================
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"   # tools/fonts
ROOT="$(cd "$HERE/../.." && pwd)"                       # racine du repo
GEN="$HERE/ttf2gfx.py"
SRC="$HERE"                                             # TTF source = ce dossier
OUT="$ROOT/include/fonts"

# Choix de l'interpréteur : $PYTHON, sinon le venv du projet, sinon python3.
if [ -n "${PYTHON:-}" ]; then
  PY="$PYTHON"
elif [ -x "$ROOT/.venv/bin/python" ]; then
  PY="$ROOT/.venv/bin/python"
else
  PY="python3"
fi

mkdir -p "$OUT"

# Liste des polices à générer : "fichier_ttf  taille_pt  nom_symbole"
# Le nom du symbole = nom du fichier d'en-tête (sans .h) et du GFXfont.
gen() {
  local ttf="$1" size="$2" name="$3"
  echo ">> $name (${size}pt) <- $ttf"
  "$PY" "$GEN" "$SRC/$ttf" "$size" --name "$name" -o "$OUT/$name.h"
}

gen FreeMonoBold.ttf  9  FreeMonoBold9pt
gen FreeMonoBold.ttf 12  FreeMonoBold12pt
gen FreeMonoBold.ttf 18  FreeMonoBold18pt

echo "OK — en-têtes générés dans include/fonts/"

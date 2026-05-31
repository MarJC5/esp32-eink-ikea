# Polices source (TTF)

Fichiers `.ttf` utilisés par `tools/ttf2gfx.py` pour générer les en-têtes
Adafruit GFX dans `include/fonts/`. Versionnés ici pour rendre la génération
reproductible (cf. `tools/gen_fonts.sh`).

## FreeMonoBold.ttf

- **Source** : GNU FreeFont, release `20120503`
  (https://ftp.gnu.org/gnu/freefont/freefont-ttf-20120503.zip)
- **Licence** : GPLv3+ **avec l'exception de police** — l'embarquement de la
  police dans un firmware/document n'impose pas la GPL à ce dernier.
- C'est la même famille que celle livrée avec la lib Adafruit GFX
  (`FreeMonoBold9pt7b` / `12pt`), d'où un rendu quasi identique. Le rasteriseur
  mono d'une version récente de FreeType arrondit ±1 px sur quelques glyphes
  diagonaux (`/ \ ^ 5`) ; `xAdvance` reste identique, donc la mise en page est
  inchangée.

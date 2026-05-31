// =====================================================================
//  scene.cpp — ★ LE SEUL FICHIER À ÉDITER POUR CHANGER L'ÉCRAN ★
//  Écran 384 x 168 px (paysage), origine (0,0) en haut à gauche.
// =====================================================================
#include "scene.h"
#include "display_hal.h"
#include "text.h"
#include "image.h"
#include "grid.h"
#include "netclock.h"
#include "images.h"
#include "grids.h"

void drawContent() {
  // Image data/images/image.png — tramage 3 couleurs (N/B/R) plein écran.
  drawImageBW(0, 0, PHOTO_black, PHOTO_W, PHOTO_H);
  drawImageRed(0, 0, PHOTO_red, PHOTO_W, PHOTO_H);

  // --- Exemples de texte (polices locales include/fonts/) ---------------
  // (x,y) = ligne de base ; styles : TEXT_SMALL / TEXT_MEDIUM / TEXT_LARGE.
  //   printText(4, 20, "Bonjour", EPD_BLACK, TEXT_LARGE);
  //   printTextCentered(60, "Titre centre", EPD_RED, TEXT_MEDIUM);
  //   printTextWrapped(4, 90, SCREEN_W - 8,
  //                    "Texte long qui passe automatiquement a la ligne "
  //                    "sans depasser la largeur de l'ecran.",
  //                    EPD_BLACK, TEXT_SMALL);
}

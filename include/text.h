#pragma once
// =====================================================================
//  text — écriture de texte sur l'écran (polices locales include/fonts/).
//  Repère paysage 384 x 168 px ; (x,y) = ligne de base (baseline) du texte.
// =====================================================================
#include <Arduino.h>

// Styles de texte -> polices locales (générées par tools/ttf2gfx.py).
enum TextStyle {
  TEXT_SMALL,    // FreeMonoBold 9pt   (hauteur de ligne 18 px)
  TEXT_MEDIUM,   // FreeMonoBold 12pt  (24 px)
  TEXT_LARGE,    // FreeMonoBold 18pt  (35 px)
};

// Écrit du texte à partir de la ligne de base (x,y).
//   color : EPD_BLACK ou EPD_RED (cf. config.h)
void printText(int16_t x, int16_t y, const char *txt,
               uint16_t color, TextStyle style = TEXT_SMALL);

// Écrit du texte centré horizontalement sur la largeur de l'écran (SCREEN_W),
// à la ligne de base y.
void printTextCentered(int16_t y, const char *txt,
                       uint16_t color, TextStyle style = TEXT_SMALL);

// Écrit du texte avec retour à la ligne automatique : coupe sur les espaces
// pour ne pas dépasser maxWidth (px). Gère aussi les '\n' explicites.
// Renvoie la ligne de base y juste APRÈS le dernier bloc écrit (= y de la
// prochaine ligne disponible).
int16_t printTextWrapped(int16_t x, int16_t y, int16_t maxWidth,
                         const char *txt, uint16_t color,
                         TextStyle style = TEXT_SMALL);

// Mesure la boîte englobante du texte rendu (px), sans rien dessiner.
// w et/ou h peuvent être nullptr.
void measureText(const char *txt, TextStyle style, int16_t *w, int16_t *h);

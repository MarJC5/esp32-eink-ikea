#pragma once
// =====================================================================
//  text — écriture de texte sur l'écran.
// =====================================================================
#include <Arduino.h>

// Écrit du texte à partir de la ligne de base (x,y).
//   color   : EPD_BLACK ou EPD_RED (cf. config.h)
//   fontBig : false = police 9pt, true = police 12pt
void printText(int16_t x, int16_t y, const char *txt,
               uint16_t color, bool fontBig = false);

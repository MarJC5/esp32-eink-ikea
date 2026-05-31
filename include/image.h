#pragma once
// =====================================================================
//  image — affichage de bitmaps (depuis include/images.h).
// =====================================================================
#include <Arduino.h>

// Dessine un bitmap 1bpp en NOIR.
void drawImageBW(int16_t x, int16_t y, const unsigned char *bmp,
                 int16_t w, int16_t h);

// Dessine un bitmap 1bpp en ROUGE.
void drawImageRed(int16_t x, int16_t y, const unsigned char *bmp,
                  int16_t w, int16_t h);

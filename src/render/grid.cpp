#include "grid.h"
#include "display_hal.h"
#include <pgmspace.h>

// Matrice de Bayer 8x8 (tramage ordonné), valeurs 0..63.
static const uint8_t BAYER8[8][8] = {
  {  0, 32,  8, 40,  2, 34, 10, 42 },
  { 48, 16, 56, 24, 50, 18, 58, 26 },
  { 12, 44,  4, 36, 14, 46,  6, 38 },
  { 60, 28, 52, 20, 62, 30, 54, 22 },
  {  3, 35, 11, 43,  1, 33,  9, 41 },
  { 51, 19, 59, 27, 49, 17, 57, 25 },
  { 15, 47,  7, 39, 13, 45,  5, 37 },
  { 63, 31, 55, 23, 61, 29, 53, 21 },
};

// Encre à utiliser pour un chiffre donné (option rouge au-delà d'un seuil).
static uint16_t inkFor(uint8_t v) {
#if GRID_RED_FROM > 0
  if (v >= GRID_RED_FROM) return EPD_RED;
#endif
  return GRID_INK_COLOR;
}

// Détermine la taille de cellule : explicite > config > auto-fit dans la zone.
static int16_t resolveCellPx(uint16_t cols, uint16_t rows,
                             int16_t x, int16_t y, int16_t cellPx) {
  if (cellPx > 0) return cellPx;
  if (GRID_CELL_PX > 0) return GRID_CELL_PX;
  int16_t availW = SCREEN_W - x;
  int16_t availH = SCREEN_H - y;
  int16_t byW = cols ? availW / (int16_t)cols : 1;
  int16_t byH = rows ? availH / (int16_t)rows : 1;
  int16_t s = byW < byH ? byW : byH;
  return s < 1 ? 1 : s;
}

// Remplit un bloc [bx,by]..(taille s) avec une densité d (0..9) par tramage.
static void fillCell(int16_t bx, int16_t by, int16_t s, uint8_t v) {
  if (v == 0) return;                 // vide -> rien (fond blanc)
  GFXcanvas1 &plane = planeFor(inkFor(v));
  // Seuil : pixel encré si (v/9)*64 > bayer. v=9 -> 64 > tout -> plein.
  uint16_t thr = (uint16_t)v * 64u / 9u;
  for (int16_t py = 0; py < s; py++) {
    int16_t Y = by + py;
    if (Y < 0 || Y >= (int16_t)SCREEN_H) continue;
    for (int16_t px = 0; px < s; px++) {
      int16_t X = bx + px;
      if (X < 0 || X >= (int16_t)SCREEN_W) continue;
      if (thr > BAYER8[Y & 7][X & 7]) plane.drawPixel(X, Y, 1);
    }
  }
}

void drawDigitGrid(const uint8_t *cells, uint16_t cols, uint16_t rows,
                   int16_t x, int16_t y, int16_t cellPx) {
  if (!cells || !cols || !rows) return;
  int16_t s = resolveCellPx(cols, rows, x, y, cellPx);
  for (uint16_t r = 0; r < rows; r++) {
    for (uint16_t c = 0; c < cols; c++) {
      uint8_t v = pgm_read_byte(&cells[(uint32_t)r * cols + c]);
      if (v > 9) v = 9;
      fillCell(x + (int16_t)c * s, y + (int16_t)r * s, s, v);
    }
  }
}

// Remplit un rectangle [x0,x1)x[y0,y1) avec une densité v (0..9) par tramage.
static void fillRectDither(int16_t x0, int16_t y0, int16_t x1, int16_t y1, uint8_t v) {
  if (v == 0) return;
  GFXcanvas1 &plane = planeFor(inkFor(v));
  uint16_t thr = (uint16_t)v * 64u / 9u;
  for (int16_t Y = y0; Y < y1; Y++) {
    if (Y < 0 || Y >= (int16_t)SCREEN_H) continue;
    for (int16_t X = x0; X < x1; X++) {
      if (X < 0 || X >= (int16_t)SCREEN_W) continue;
      if (thr > BAYER8[Y & 7][X & 7]) plane.drawPixel(X, Y, 1);
    }
  }
}

void drawDigitGridFill(const uint8_t *cells, uint16_t cols, uint16_t rows,
                       int16_t x, int16_t y, int16_t w, int16_t h) {
  if (!cells || !cols || !rows || w <= 0 || h <= 0) return;
  for (uint16_t r = 0; r < rows; r++) {
    int16_t Y0 = y + (int16_t)((int32_t)r * h / rows);
    int16_t Y1 = y + (int16_t)((int32_t)(r + 1) * h / rows);
    for (uint16_t c = 0; c < cols; c++) {
      int16_t X0 = x + (int16_t)((int32_t)c * w / cols);
      int16_t X1 = x + (int16_t)((int32_t)(c + 1) * w / cols);
      uint8_t v = pgm_read_byte(&cells[(uint32_t)r * cols + c]);
      if (v > 9) v = 9;
      fillRectDither(X0, Y0, X1, Y1, v);
    }
  }
}

void drawDigitGridText(const char *ascii, int16_t x, int16_t y,
                       int16_t cellPx) {
  if (!ascii) return;
  // 1er passage : déterminer cols (max sur une ligne) et rows.
  uint16_t rows = 0, cols = 0, curCols = 0;
  for (const char *p = ascii; *p; ++p) {
    if (*p == '\n') {
      if (curCols > cols) cols = curCols;
      if (curCols > 0) rows++;
      curCols = 0;
    } else if (*p >= '0' && *p <= '9') {
      curCols++;
    }
  }
  if (curCols > 0) { if (curCols > cols) cols = curCols; rows++; }
  if (!rows || !cols) return;

  int16_t s = resolveCellPx(cols, rows, x, y, cellPx);
  // 2e passage : dessin direct, sans buffer (économise la RAM).
  uint16_t r = 0, c = 0;
  for (const char *p = ascii; *p; ++p) {
    if (*p == '\n') { if (c > 0) { r++; c = 0; } }
    else if (*p >= '0' && *p <= '9') {
      fillCell(x + (int16_t)c * s, y + (int16_t)r * s, s, (uint8_t)(*p - '0'));
      c++;
    }
  }
}

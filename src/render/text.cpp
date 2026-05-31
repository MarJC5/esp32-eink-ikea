#include "text.h"
#include "display_hal.h"
#include "fonts/FreeMonoBold9pt.h"
#include "fonts/FreeMonoBold12pt.h"
#include "fonts/FreeMonoBold18pt.h"
#include <string.h>

// Style -> police GFX locale.
static const GFXfont *fontFor(TextStyle style) {
  switch (style) {
    case TEXT_LARGE:  return &FreeMonoBold18pt;
    case TEXT_MEDIUM: return &FreeMonoBold12pt;
    case TEXT_SMALL:
    default:          return &FreeMonoBold9pt;
  }
}

void printText(int16_t x, int16_t y, const char *txt,
               uint16_t color, TextStyle style) {
  GFXcanvas1 &p = planeFor(color);
  p.setFont(fontFor(style));
  p.setTextColor(1);            // 1 = couleur présente dans ce plan
  p.setCursor(x, y);
  p.print(txt);
}

void measureText(const char *txt, TextStyle style, int16_t *w, int16_t *h) {
  // Géométrie/metrics identiques sur les 2 plans ; on mesure sur le plan noir.
  GFXcanvas1 &p = planeFor(EPD_BLACK);
  p.setFont(fontFor(style));
  int16_t x1, y1;
  uint16_t bw, bh;
  p.getTextBounds(txt, 0, 0, &x1, &y1, &bw, &bh);
  if (w) *w = (int16_t)bw;
  if (h) *h = (int16_t)bh;
}

void printTextCentered(int16_t y, const char *txt,
                       uint16_t color, TextStyle style) {
  GFXcanvas1 &p = planeFor(color);
  p.setFont(fontFor(style));
  p.setTextColor(1);
  int16_t x1, y1;
  uint16_t bw, bh;
  p.getTextBounds(txt, 0, y, &x1, &y1, &bw, &bh);
  // Centre la boîte encrée : bord gauche voulu = (SCREEN_W - bw)/2.
  int16_t x = (int16_t)((SCREEN_W - (int)bw) / 2) - x1;
  p.setCursor(x, y);
  p.print(txt);
}

int16_t printTextWrapped(int16_t x, int16_t y, int16_t maxWidth,
                         const char *txt, uint16_t color, TextStyle style) {
  GFXcanvas1 &p = planeFor(color);
  const GFXfont *f = fontFor(style);
  p.setFont(f);
  p.setTextColor(1);
  const int16_t lineH = (int16_t)pgm_read_byte(&f->yAdvance);
  int16_t cy = y;

  char line[160];           // ligne en cours de construction
  size_t lineLen = 0;
  line[0] = '\0';

  auto flush = [&]() {
    if (lineLen > 0) {
      p.setCursor(x, cy);
      p.print(line);
    }
    cy += lineH;
    lineLen = 0;
    line[0] = '\0';
  };

  const char *s = txt;
  while (*s) {
    if (*s == '\n') { flush(); s++; continue; }
    if (*s == ' ')  { s++; continue; }   // espaces (séparateurs) normalisés

    // mot = séquence de non-espaces
    const char *e = s;
    while (*e && *e != ' ' && *e != '\n') e++;
    size_t wlen = (size_t)(e - s);

    // ligne candidate = line + (espace si line non vide) + mot
    char cand[160];
    size_t cl = (lineLen < sizeof(cand)) ? lineLen : sizeof(cand) - 1;
    memcpy(cand, line, cl);
    if (cl > 0 && cl < sizeof(cand) - 1) cand[cl++] = ' ';
    size_t take = wlen;
    if (cl + take > sizeof(cand) - 1) take = sizeof(cand) - 1 - cl;
    memcpy(cand + cl, s, take);
    cl += take;
    cand[cl] = '\0';

    int16_t x1, y1;
    uint16_t bw, bh;
    p.getTextBounds(cand, 0, 0, &x1, &y1, &bw, &bh);

    if ((int16_t)bw > maxWidth && lineLen > 0) {
      flush();                       // la ligne courante est pleine
      take = (wlen < sizeof(line)) ? wlen : sizeof(line) - 1;
      memcpy(line, s, take);
      lineLen = take;
      line[lineLen] = '\0';          // le mot démarre la nouvelle ligne
    } else {
      memcpy(line, cand, cl + 1);    // accepte la candidate
      lineLen = cl;
    }
    s = e;
  }
  flush();                           // dernier bloc
  return cy;
}

#include "image.h"
#include "display_hal.h"

void drawImageBW(int16_t x, int16_t y, const unsigned char *bmp,
                 int16_t w, int16_t h) {
  gfxBlack.drawBitmap(x, y, bmp, w, h, 1);
}

void drawImageRed(int16_t x, int16_t y, const unsigned char *bmp,
                  int16_t w, int16_t h) {
  gfxRed.drawBitmap(x, y, bmp, w, h, 1);
}

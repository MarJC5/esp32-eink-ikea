#include "text.h"
#include "display_hal.h"
#include <Fonts/FreeMonoBold9pt7b.h>
#include <Fonts/FreeMonoBold12pt7b.h>

void printText(int16_t x, int16_t y, const char *txt,
               uint16_t color, bool fontBig) {
  GFXcanvas1 &p = planeFor(color);
  p.setFont(fontBig ? &FreeMonoBold12pt7b : &FreeMonoBold9pt7b);
  p.setTextColor(1);            // 1 = couleur présente dans ce plan
  p.setCursor(x, y);
  p.print(txt);
}

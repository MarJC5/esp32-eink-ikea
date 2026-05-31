#include "display_hal.h"
#include "epd_driver.h"

// Deux plans 1 bit/pixel (Adafruit GFX) : noir et rouge.
// Alloués en taille NATIVE (168x384) ; on tourne en paysage via setRotation.
GFXcanvas1 gfxBlack(NATIVE_W, NATIVE_H);
GFXcanvas1 gfxRed(NATIVE_W, NATIVE_H);

void initDisplay() {
  epdInit();
  gfxBlack.setRotation(CANVAS_ROT);
  gfxRed.setRotation(CANVAS_ROT);
}

void epdShow() {
  epdDisplay(gfxBlack.getBuffer(), gfxRed.getBuffer());
  epdSleep();
}

GFXcanvas1& planeFor(uint16_t color) {
  return (color == EPD_RED) ? gfxRed : gfxBlack;
}

void showRawPlanes(const uint8_t* black, const uint8_t* red) {
  epdInit();                    // réveille la dalle (deep sleep -> reset)
  epdDisplay(black, red);
  epdSleep();
}

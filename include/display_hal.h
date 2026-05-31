#pragma once
// =====================================================================
//  display_hal — rendu via Adafruit GFX sur 2 plans (noir + rouge),
//  poussés vers la dalle e-ink (driver: include/epd_driver.h).
// =====================================================================
#include <Adafruit_GFX.h>
#include "config.h"

// Dalle e-ink 168 x 384 natif (portrait), contrôleur UC8151.
// On dessine en PAYSAGE 384 x 168 (rotation 1 du canvas).
static const uint16_t NATIVE_W = 168;
static const uint16_t NATIVE_H = 384;
static const uint16_t SCREEN_W = 384;   // largeur logique (paysage)
static const uint16_t SCREEN_H = 168;   // hauteur logique

// Plans de dessin : un pour le noir, un pour le rouge (bit=1 => couleur).
extern GFXcanvas1 gfxBlack;
extern GFXcanvas1 gfxRed;

void initDisplay();                    // init SPI + dalle
void epdShow();                        // pousse les 2 plans (gfx) + met en veille
GFXcanvas1& planeFor(uint16_t color);  // EPD_BLACK -> gfxBlack, EPD_RED -> gfxRed

// Affiche 2 plans BRUTS (format natif attendu par epdDisplay : 21 oct/ligne x 384),
// reçus par push série, sans passer par les canvas GFX.
void showRawPlanes(const uint8_t* black, const uint8_t* red);

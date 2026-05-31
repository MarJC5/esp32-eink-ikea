#pragma once
// =====================================================================
//  epd_driver — INTERFACE commune des drivers d'écran e-ink.
//  Chaque modèle de dalle a son implémentation dans src/drivers/<modele>.cpp
//  (un seul compilé à la fois). Le HAL (display_hal) ne dépend que de cette
//  interface, pas d'un modèle précis.
//
//  Convention des plans : canvas Adafruit GFX 1 bit/pixel, bit=1 -> couleur.
// =====================================================================
#include <Arduino.h>

void epdInit();                                       // reset + séquence d'init
void epdClear();                                      // efface tout (blanc)
void epdDisplay(const uint8_t* black, const uint8_t* red);  // pousse les 2 plans + refresh
void epdSleep();                                      // deep sleep
void epdReplLoop();                                   // REPL série bas niveau (diagnostic)

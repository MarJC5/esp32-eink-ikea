// =====================================================================
//  ESP32 + écran e-ink 168x384 (UC8151, 3 couleurs N/B/R)
//  Driver écran : src/drivers/ (interface include/epd_driver.h).
//
//  Pour MODIFIER l'affichage : édite src/scene.cpp -> drawContent().
//  Réglages : include/config.h.
// =====================================================================
#include <Arduino.h>
#include "display_hal.h"
#include "scene.h"
#include "netclock.h"
#include "epd_driver.h"
#include "config.h"

void setup() {
  Serial.begin(115200);
  delay(200);
  Serial.println("\n[ESP32 e-ink] demarrage (2.9b 168x384)");

#if EPD_REPL
  epdReplLoop();   // mode diagnostic : ne revient jamais
#endif

  initDisplay();

#if USE_WIFI
  connectWifiAndTime();
#endif

#if SHOW_DEFAULT
  // Dessine le contenu de scene.cpp au démarrage.
  gfxBlack.fillScreen(0);
  gfxRed.fillScreen(0);
  drawContent();
  Serial.println("[ESP32 e-ink] envoi vers la dalle (~25 s)...");
  epdShow();
  Serial.println("[ESP32 e-ink] termine.");
#endif

  Serial.setTimeout(8000);     // pour readBytes pendant un push
  Serial.println("[PUSH] pret");   // <- l'hôte (show.py) attend ce marqueur
}

// ---------------------------------------------------------------------
//  Push série : en-tête "EPDF" + uint16 w + uint16 h (little-endian) +
//  plan NOIR (w/8*h octets) + plan ROUGE (idem). Affiche l'image reçue.
// ---------------------------------------------------------------------
static const uint32_t PLANE_BYTES = (uint32_t)(NATIVE_W / 8) * NATIVE_H;  // 21*384 = 8064
static uint8_t blackBuf[PLANE_BYTES];
static uint8_t redBuf[PLANE_BYTES];

static void receiveFrame() {
  uint8_t hdr[4];
  if (Serial.readBytes(hdr, 4) != 4) return;
  uint16_t w = hdr[0] | (hdr[1] << 8);
  uint16_t h = hdr[2] | (hdr[3] << 8);
  uint32_t plane = (uint32_t)(w / 8) * h;
  if (plane != PLANE_BYTES) {
    Serial.print("[PUSH] taille inattendue "); Serial.print(w); Serial.print("x"); Serial.println(h);
    return;
  }
  if (Serial.readBytes(blackBuf, PLANE_BYTES) != PLANE_BYTES) { Serial.println("[PUSH] noir incomplet"); return; }
  if (Serial.readBytes(redBuf, PLANE_BYTES)   != PLANE_BYTES) { Serial.println("[PUSH] rouge incomplet"); return; }
  Serial.println("[PUSH] rendu...");
  showRawPlanes(blackBuf, redBuf);
  Serial.println("[PUSH] pret");
}

void loop() {
  // Cherche le magic "EPDF" en flux, puis lit la trame.
  static const char MAGIC[4] = {'E', 'P', 'D', 'F'};
  static int mi = 0;
  while (Serial.available()) {
    int c = Serial.read();
    if (c == MAGIC[mi]) {
      if (++mi == 4) { mi = 0; receiveFrame(); }
    } else {
      mi = (c == MAGIC[0]) ? 1 : 0;
    }
  }
  delay(5);
}

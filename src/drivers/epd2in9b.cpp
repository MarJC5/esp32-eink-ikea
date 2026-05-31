#include "config.h"
#if EPD_MODEL == EPD_2IN9
#include "epd_driver.h"
#include <SPI.h>

// =====================================================================
//  Dalle Waveshare 2.9" (B) — 168 x 384, 3 couleurs (N/B/R), contrôleur UC8151.
//  Portage FIDÈLE de la démo officielle Waveshare epd2in9b_V3 :
//    - 2 plans 1bpp : Noir/Blanc (0x10) + Rouge (0x13).
//    - power on 0x04, panel setting 0x00, résolution 0x61, CDI 0x50.
//    - refresh 0x12 ; BUSY lu via la commande 0x71 (idle = pin HIGH).
//  Buffers gfxBlack/gfxRed : 21 octets/ligne (168 px) x 384 lignes.
//  Polarité : encre(1) -> 0 (envoi ~plan). 0xFF = blanc / pas de rouge.
// =====================================================================

static const int PITCH = 21;    // 168 px / 8 = 21 octets/ligne
static const int ROWS  = 384;   // hauteur native

static inline void cmd(uint8_t c) {
  digitalWrite(EPD_DC, LOW);  digitalWrite(EPD_CS, LOW);
  SPI.transfer(c);            digitalWrite(EPD_CS, HIGH);
}
static inline void data(uint8_t d) {
  digitalWrite(EPD_DC, HIGH); digitalWrite(EPD_CS, LOW);
  SPI.transfer(d);            digitalWrite(EPD_CS, HIGH);
}

// UC8151 : idle quand, après commande 0x71, le pin BUSY est HIGH (bit0=1).
static void waitIdle(uint32_t timeout_ms) {
  uint32_t t0 = millis();
  for (;;) {
    cmd(0x71);
    if (digitalRead(EPD_BUSY)) break;       // HIGH = libre
    if (millis() - t0 > timeout_ms) { Serial.println("[BUSY] timeout!"); break; }
    delay(10);
  }
  delay(200);
}

static void reset() {
  digitalWrite(EPD_RST, HIGH); delay(200);
  digitalWrite(EPD_RST, LOW);  delay(5);
  digitalWrite(EPD_RST, HIGH); delay(200);
}

void epdInit() {
  // SPI initialisé UNE seule fois : beginTransaction prend le mutex SPI ; le
  // rappeler sans endTransaction -> deadlock. epdInit peut être ré-appelé
  // (ex. showRawPlanes après un push) pour ré-init la dalle sans toucher au SPI.
  static bool spiReady = false;
  if (!spiReady) {
    pinMode(EPD_CS, OUTPUT);
    pinMode(EPD_DC, OUTPUT);
    pinMode(EPD_RST, OUTPUT);
    pinMode(EPD_BUSY, INPUT);
    digitalWrite(EPD_CS, HIGH);
    SPI.begin(EPD_SCK, -1, EPD_MOSI, EPD_CS);
    SPI.beginTransaction(SPISettings(2000000, MSBFIRST, SPI_MODE0));
    spiReady = true;
  }

  reset();
  cmd(0x04);                               // POWER ON
  delay(300);                              // (BUSY 0x71 non fiable sur dalle nue -> délai fixe)
  cmd(0x00); data(0x0f); data(0x89);       // panel setting
  cmd(0x61); data(0xA8); data(0x01); data(0x80);   // résolution 168 x 384
  cmd(0x50); data(0x77);                   // VCOM / data interval
}

void epdDisplay(const uint8_t* black, const uint8_t* red) {
  cmd(0x10);                               // plan Noir/Blanc
  for (int j = 0; j < ROWS; j++)
    for (int i = 0; i < PITCH; i++) data((uint8_t)~black[j * PITCH + i]);
  cmd(0x92);
  cmd(0x13);                               // plan Rouge
  for (int j = 0; j < ROWS; j++)
    for (int i = 0; i < PITCH; i++) data((uint8_t)~red[j * PITCH + i]);
  cmd(0x92);
  cmd(0x12);                               // refresh
  delay(16000);                            // refresh complet 3 couleurs (~15 s), BUSY ignoré
}

void epdClear() {}

void epdSleep() {
  cmd(0x02); waitIdle(5000);               // power off
  cmd(0x07); data(0xA5);                   // deep sleep
}

// =====================================================================
//  REPL série bas niveau (diagnostic). Activé par EPD_REPL dans config.h.
//    R reset | b busy | cXX cmd | dXX data | nXX,KKKK fill
// =====================================================================
void epdReplLoop() {
  pinMode(EPD_CS, OUTPUT);
  pinMode(EPD_DC, OUTPUT);
  pinMode(EPD_RST, OUTPUT);
  pinMode(EPD_BUSY, INPUT);
  digitalWrite(EPD_CS, HIGH);
  SPI.begin(EPD_SCK, -1, EPD_MOSI, EPD_CS);
  SPI.beginTransaction(SPISettings(2000000, MSBFIRST, SPI_MODE0));
  Serial.println("[REPL] pret. R b cXX dXX nXX,KKKK");
  String line;
  for (;;) {
    if (!Serial.available()) { delay(2); continue; }
    line = Serial.readStringUntil('\n'); line.trim();
    if (line.length() == 0) continue;
    char op = line[0];
    String arg = line.substring(1); arg.trim();
    if (op == 'R') { reset(); Serial.print("[R] busy="); Serial.println(digitalRead(EPD_BUSY)); }
    else if (op == 'b') { Serial.print("[b] busy="); Serial.println(digitalRead(EPD_BUSY)); }
    else if (op == 'c') { uint8_t x=(uint8_t)strtol(arg.c_str(),nullptr,16); cmd(x); Serial.print("[c] "); Serial.println(x,HEX); }
    else if (op == 'd') { uint8_t x=(uint8_t)strtol(arg.c_str(),nullptr,16); data(x); Serial.print("[d] "); Serial.println(x,HEX); }
    else if (op == 'n') { int comma=arg.indexOf(','); uint8_t x=(uint8_t)strtol(arg.substring(0,comma).c_str(),nullptr,16);
      long k=atol(arg.substring(comma+1).c_str()); for(long i=0;i<k;i++) data(x); Serial.print("[n] done"); Serial.println(k); }
    else { Serial.print("[?] "); Serial.println(line); }
  }
}

#endif // EPD_MODEL == EPD_2IN9

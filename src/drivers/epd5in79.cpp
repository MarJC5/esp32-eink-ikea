#include "config.h"
#if EPD_MODEL == EPD_5IN79
#include "epd_driver.h"
#include <SPI.h>

// =====================================================================
//  Dalle e-ink 5.79" — 792 x 272, DOUBLE contrôleur HX8717, 3 couleurs (N/B/R).
//  Portage de la démo officielle Waveshare epd5in79g (4 couleurs ; on n'utilise
//  que 3 codes : noir/blanc/rouge, jamais jaune) :
//    - données 2 bits/pixel sur le plan 0x10 ; partition via 0xa2 (01 master /
//      02 slave / 00 broadcast) ; refresh 0x12.
//    - envoi ENTRELACÉ : master = lignes (j, 271-j) pour j<136 ; slave idem,
//      moitié droite (offset +99 octets).
//  BUSY non fiable (dalle nue) -> DÉLAIS FIXES (pas de lecture BUSY).
//  Les 2 plans 1bpp du projet (gfxBlack/gfxRed, 792x272, 99 o/ligne) sont
//  convertis à la volée en 2bpp : rouge -> 0b11 ; noir -> 0b00 ; sinon 0b01.
// =====================================================================

static const int PITCH    = 99;     // 792 px / 8 = 99 octets/ligne (plans 1bpp)
static const int HALF_BC  = 99;     // octets 2bpp par DEMI-ligne (396 px / 4)
static const int ROWS     = 272;
static const uint32_t REFRESH_MS = 24000;   // refresh complet (BUSY ignoré)

static inline void cmd(uint8_t c) {
  digitalWrite(EPD_DC, LOW);  digitalWrite(EPD_CS, LOW);
  SPI.transfer(c);            digitalWrite(EPD_CS, HIGH);
}
static inline void data(uint8_t d) {
  digitalWrite(EPD_DC, HIGH); digitalWrite(EPD_CS, LOW);
  SPI.transfer(d);            digitalWrite(EPD_CS, HIGH);
}

static void reset() {
  digitalWrite(EPD_RST, HIGH); delay(200);
  digitalWrite(EPD_RST, LOW);  delay(5);
  digitalWrite(EPD_RST, HIGH); delay(200);
}

void epdInit() {
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
  delay(100);
  // Init LONGUE (epd579yr / bb_epaper) : c'est elle qui alimente CETTE dalle
  // (PWRR 0x01 + BTST 0xc0 + gamma). Config envoyée aux DEUX contrôleurs.
  cmd(0xe0); data(0x01);
  for (int s = 0; s < 2; s++) {
    cmd(0xa2); data(s == 0 ? 0x01 : 0x02);
    cmd(0x00); data(s == 0 ? 0x07 : 0x03); data(0x29);                               // PSR
    cmd(0x01); data(0x07); data(0x00); data(0x26); data(0x78); data(0x24); data(0x26); // PWRR
    cmd(0x06); data(0xc0); data(0xc0); data(0xc0);                                   // BTST
    cmd(0x50); data(0x97);                                                           // CDI
    cmd(0x61); data(0x01); data(0x8C); data(0x01); data(0x10);                       // TRES 396x272
    cmd(0x65); data(0x00); data(0x00); data(0x00); data(0x00);                       // GSST
    cmd(0xe3); data(0x77);
    cmd(0xff); data(0xa5);
    cmd(0xef); data(1); data(30); data(6); data(30); data(14); data(28); data(18); data(16);
    cmd(0xdb); data(0x00);
    cmd(0xcf); data(0x00);
    cmd(0xdf); data(0x00);
    cmd(0xfd); data(0x01);
    cmd(0xe8); data(0x03);
    cmd(0xdc); data(0x00);
    cmd(0xdd); data(10);
    cmd(0xde); data(60);
    cmd(0xff); data(0xe3);
    cmd(0xe9); data(0x01);
    cmd(0x04);                                       // POWER ON contrôleur
    delay(300);
    cmd(0xa2); data(0x00);
  }
}

// Octet 2bpp (4 pixels) pour la colonne d'octet `bc` (0..197) et la ligne `row`.
static inline uint8_t pack2bpp(const uint8_t* black, const uint8_t* red, int bc, int row) {
  const int rowBase = row * PITCH;
  const int x0 = bc * 4;
  uint8_t out = 0;
  for (int p = 0; p < 4; p++) {
    int x = x0 + p;
    uint8_t mask = 0x80 >> (x & 7);
    int idx = rowBase + (x >> 3);
    uint8_t code;
    if      (red[idx]   & mask) code = 0x3;   // rouge
    else if (black[idx] & mask) code = 0x0;   // noir
    else                        code = 0x1;   // blanc
    out = (out << 2) | code;
  }
  return out;
}

// Fenêtre RAM d'un contrôleur (0xA2 select + 0x83). select : 01 master / 02 slave / 00 both.
static void setRamArea(uint8_t select, uint16_t x, uint16_t y, uint16_t w, uint16_t h, bool partial) {
  cmd(0xA2); data(select);
  cmd(0x83);
  data(x / 256);           data(x % 256);
  data((x + w - 1) / 256); data((x + w - 1) % 256);
  data(y / 256);           data(y % 256);
  data((y + h - 1) / 256); data((y + h - 1) % 256);
  data(partial ? 0x01 : 0x00);
}

void epdDisplay(const uint8_t* black, const uint8_t* red) {
  const int HALF_W = 396;   // px par contrôleur
  // Chaque ligne source est envoyée DEUX FOIS (la RAM gate fait 2x la hauteur) :
  // copie 1 = ligne (271-j) [flip], copie 2 = ligne j.  -> 544 lignes / moitié.

  // ----- MASTER : moitié gauche (octets 0..98) -----
  setRamArea(0x01, 0, 0, HALF_W, ROWS, false);
  cmd(0x10);
  for (int j = 0; j < ROWS; j++) {
    int r1 = ROWS - 1 - j;
    for (int i = 0; i < HALF_BC; i++) data(pack2bpp(black, red, i, r1));
    for (int i = 0; i < HALF_BC; i++) data(pack2bpp(black, red, i, j));
  }
  // ----- SLAVE : moitié droite (octets 99..197), fenêtre à x=0 -----
  setRamArea(0x02, 0, 0, HALF_W, ROWS, false);
  cmd(0x10);
  for (int j = 0; j < ROWS; j++) {
    int r1 = ROWS - 1 - j;
    for (int i = 0; i < HALF_BC; i++) data(pack2bpp(black, red, i + HALF_BC, r1));
    for (int i = 0; i < HALF_BC; i++) data(pack2bpp(black, red, i + HALF_BC, j));
  }
  // ----- REFRESH plein écran (broadcast) -----
  setRamArea(0x00, 0, 0, HALF_W, ROWS, false);
  cmd(0x50); data(0x37);     // CDI full-refresh
  cmd(0x04); delay(300);     // POWER ON
  cmd(0x12); data(0x00);
  delay(REFRESH_MS);
}

void epdClear() {}

void epdSleep() {
  cmd(0x02); data(0x00); delay(100);   // power off
  cmd(0x07); data(0xA5);               // deep sleep
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

#endif // EPD_MODEL == EPD_5IN79

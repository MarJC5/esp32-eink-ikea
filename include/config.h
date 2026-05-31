#pragma once
// =====================================================================
//  config.h — TOUS les réglages du projet sont ici.
//  Édite ce fichier pour changer les pins, le modèle d'écran ou le Wi-Fi.
// =====================================================================

// ---------------------------------------------------------------------
// 1) PINS SPI vers l'écran e-ink
//    Valeurs par défaut = câblage standard du démo Waveshare ESP32.
//    >>> Si l'écran reste blanc, vérifie ces pins avec ton câblage réel. <<<
// ---------------------------------------------------------------------
#define EPD_CS    15   // CS   (Chip Select)
#define EPD_DC    27   // DC   (Data/Command)
#define EPD_RST   26   // RST  (Reset)
#define EPD_BUSY  25   // BUSY
#define EPD_SCK   13   // CLK  (horloge SPI)
#define EPD_MOSI  14   // DIN  (données SPI, MOSI)
// (MISO non utilisé par l'e-ink -> -1)

// ---------------------------------------------------------------------
// 2) ÉCRAN : e-ink 168x384, 3 couleurs (N/B/R), contrôleur UC8151.
//    Driver : src/drivers/epd2in9b.cpp (BUSY 0x71 non fiable -> délai fixe).
//    Couleurs logiques pour les helpers de dessin :
// ---------------------------------------------------------------------
#define EPD_WHITE  0
#define EPD_BLACK  1
#define EPD_RED    2

// Mode diagnostic : 1 = REPL série bas niveau (pilotage manuel commande/donnée),
// 0 = fonctionnement normal.
#define EPD_REPL   0

// 1 = dessine drawContent() (scene.cpp) au démarrage.
// 0 = mode PUSH : n'affiche rien au boot, écoute le port série (tools/show.py).
#define SHOW_DEFAULT 0

// ---------------------------------------------------------------------
// 3) Wi-Fi (optionnel)
//    Mets USE_WIFI à 1 et renseigne tes identifiants pour afficher
//    des données dynamiques (heure NTP, API...).
// ---------------------------------------------------------------------
#define USE_WIFI   0
#define WIFI_SSID  "TON_RESEAU"
#define WIFI_PASS  "TON_MOT_DE_PASSE"

// Fuseau horaire (NTP). Exemple Suisse : CET-1CEST,M3.5.0,M10.5.0/3
#define NTP_TZ     "CET-1CEST,M3.5.0,M10.5.0/3"
#define NTP_SERVER "pool.ntp.org"

// ---------------------------------------------------------------------
// 4) Grille de chiffres 0-9 (module grid)
//    Chaque chiffre = densité de remplissage : 0=vide(blanc) ... 9=plein.
//    Rendu par tramage (dithering) -> dégradé de gris.
// ---------------------------------------------------------------------
#define GRID_INK_COLOR  EPD_BLACK     // encre du dégradé (ou EPD_RED)
#define GRID_RED_FROM   0             // 0=off ; sinon chiffres >= N tracés en rouge
#define GRID_CELL_PX    0             // 0=auto-fit ; sinon taille fixe d'une cellule (px)

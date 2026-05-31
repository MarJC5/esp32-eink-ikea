#pragma once
// =====================================================================
//  netclock — Wi-Fi + heure NTP (actif seulement si USE_WIFI=1).
// =====================================================================
#include <Arduino.h>
#include "config.h"

#if USE_WIFI
// Connecte le Wi-Fi puis synchronise l'heure via NTP. true si OK.
bool connectWifiAndTime();
// Remplit buf avec l'heure locale "JJ/MM  HH:MM". false si indispo.
bool getTimeStr(char *buf, size_t n);
#endif

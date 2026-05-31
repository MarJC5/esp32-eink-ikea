#include "netclock.h"

#if USE_WIFI
#include <WiFi.h>
#include <time.h>

bool connectWifiAndTime() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("Wi-Fi");
  for (int i = 0; i < 40 && WiFi.status() != WL_CONNECTED; i++) {
    delay(250);
    Serial.print(".");
  }
  Serial.println();
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("Wi-Fi: echec connexion");
    return false;
  }
  Serial.print("Wi-Fi OK, IP=");
  Serial.println(WiFi.localIP());
  configTzTime(NTP_TZ, NTP_SERVER);
  struct tm t;
  if (!getLocalTime(&t, 10000)) {
    Serial.println("NTP: pas d'heure");
    return false;
  }
  return true;
}

bool getTimeStr(char *buf, size_t n) {
  struct tm t;
  if (!getLocalTime(&t, 0)) return false;
  strftime(buf, n, "%d/%m  %H:%M", &t);
  return true;
}
#endif

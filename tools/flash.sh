#!/usr/bin/env bash
# Flash le firmware sur l'ESP32.
#
#   ./tools/flash.sh           # méthode normale (PlatformIO, avec stub) -> à privilégier
#   ./tools/flash.sh nostub    # flash de secours (esptool --no-stub, non compressé)
#   ./tools/flash.sh restore   # réécrit l'image de sauvegarde (dump 4 MB, backup/)
set -e
cd "$(dirname "$0")/.."

PORT=/dev/cu.wchusbserial58FD0148761
# esptool fourni par PlatformIO (tool-esptoolpy), lancé avec le python du venv.
ESPTOOL="$(ls "$HOME"/.platformio/packages/tool-esptoolpy*/esptool.py 2>/dev/null | head -1)"
PY=.venv/bin/python
BOOTAPP0="$HOME/.platformio/packages/framework-arduinoespressif32/tools/partitions/boot_app0.bin"
BUILD=.pio/build/esp32dev

case "${1:-pio}" in
  pio)
    .venv/bin/pio run -t upload
    ;;
  nostub)
    "$PY" "$ESPTOOL" --port "$PORT" --no-stub --baud 115200 \
      --before default_reset --after hard_reset write_flash --flash_size 4MB \
      0x1000  "$BUILD/bootloader.bin" \
      0x8000  "$BUILD/partitions.bin" \
      0xe000  "$BOOTAPP0" \
      0x10000 "$BUILD/firmware.bin"
    ;;
  restore)
    # Réécrit l'image de sauvegarde (efface tout puis réécrit 4 MB).
    "$PY" "$ESPTOOL" --port "$PORT" --baud 115200 \
      --before default_reset --after hard_reset write_flash --flash_size 4MB \
      0x0 backup/waveshare_demo_full_4MB.bin
    ;;
  *)
    echo "usage: $0 [pio|nostub|restore]"; exit 1;;
esac

# =====================================================================
#  Makefile — raccourcis pour le projet ESP32 e-ink.
#  Utilise le venv local (.venv). Cree-le d'abord avec : make venv
# =====================================================================
VENV    := .venv
PIO     := $(VENV)/bin/pio
PYTHON  := $(VENV)/bin/python
GRIDS   := $(wildcard data/grids/*.txt)
IMG     ?=

.PHONY: help venv build upload flash nostub restore monitor grids check img fonts show gui backup clean

help:
	@echo "Cibles disponibles :"
	@echo "  make venv      installe PlatformIO + Pillow + pyserial dans .venv"
	@echo "  make build     compile (pio run)"
	@echo "  make upload    compile + flashe (alias: make flash)"
	@echo "  make nostub    flash de secours esptool --no-stub"
	@echo "  make restore   reecrit l'image de sauvegarde (dump 4MB, backup/)"
	@echo "  make monitor   moniteur serie (115200)"
	@echo "  make grids     regenere include/grids.h depuis data/grids/*.txt"
	@echo "  make check     controle les dimensions des grilles (sans ecrire)"
	@echo "  make img IMG=x.png   image -> include/images.h (a coller dans scene.cpp)"
	@echo "  make fonts     regenere include/fonts/*.h depuis tools/fonts/*.ttf"
	@echo "  make show IMG=x.png  affiche une image via PUSH serie (sans reflasher)"
	@echo "  make gui       ouvre l'app de bureau (choisir image/texte + apercu + envoyer)"
	@echo "  make backup    relit 4MB de flash -> backup/"
	@echo "  make clean     nettoie le build"

venv:
	python3 -m venv $(VENV)
	$(VENV)/bin/pip install -q --upgrade pip platformio pillow
	$(VENV)/bin/pip install -q -r tools/requirements.txt
	@echo "venv pret."

build: grids
	$(PIO) run

upload flash: grids
	$(PIO) run -t upload

nostub:
	./tools/flash.sh nostub

restore:
	./tools/flash.sh restore

monitor:
	$(PIO) device monitor

grids:
	@$(PYTHON) tools/grids/txt2grid.py $(GRIDS)

check:
	@$(PYTHON) tools/grids/txt2grid.py --check --strict $(GRIDS)

img:
	@test -n "$(IMG)" || { echo "usage: make img IMG=chemin/image.png"; exit 1; }
	$(PYTHON) tools/image/img2cpp.py "$(IMG)"

fonts:
	PYTHON=$(PYTHON) ./tools/fonts/gen_fonts.sh

show:
	@test -n "$(IMG)" || { echo "usage: make show IMG=chemin/image.png"; exit 1; }
	$(PYTHON) tools/image/show.py "$(IMG)"

gui:
	$(PYTHON) tools/image/epd_gui.py

backup:
	@mkdir -p backup
	$(PYTHON) "$$(ls $$HOME/.platformio/packages/tool-esptoolpy*/esptool.py | head -1)" \
		--port /dev/cu.wchusbserial58FD0148761 --baud 115200 \
		read_flash 0x0 0x400000 backup/waveshare_demo_full_4MB.bin

clean:
	$(PIO) run -t clean

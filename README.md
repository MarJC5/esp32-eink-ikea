# ESP32 + écran e-ink 3 couleurs (168×384) — affichage facile

Pilote une dalle **e-Paper 3 couleurs (noir / blanc / rouge), 168×384 px** (affichée en **paysage
384×168**), contrôleur **UC8151**, depuis une carte **ESP32-D0WD-V3**, via **PlatformIO**.

Le rendu se fait avec **Adafruit GFX** sur deux plans 1 bit (`gfxBlack` + `gfxRed`), poussés à la dalle
par un **driver custom** (`src/drivers/epd2in9b.cpp`). Deux façons d'afficher du contenu :

1. **Dynamique — push série (recommandé)** : une commande sur l'ordi envoie une image ou du texte par
   USB, l'écran l'affiche **sans recompiler ni reflasher**.
2. **En dur** : on écrit le contenu dans `src/scene.cpp` puis on flashe.

> ⚠️ Dalle nue (récupérée, sans carte pilote) : le pin **BUSY n'est pas fiable** → on utilise des
> **délais fixes**. Chaque rafraîchissement est complet (~16 s, ça clignote) — normal sur du 3 couleurs.

---

## Installation (une fois)
```bash
make venv          # crée .venv + installe platformio, pillow, pyserial
make upload        # compile + flashe le firmware
```
Le firmware démarre en **mode push** (il écoute le port série, n'affiche rien au boot).

---

## 1) Afficher dynamiquement (push série, sans reflasher)

```bash
python tools/show.py data/images/image.png       # une image (tramage 3 couleurs par défaut)
python tools/show.py --text "Bonjour Fabrice"     # du texte
python tools/show.py photo.jpg --mode cover --red-level 120
python tools/show.py --text "PROMO -50%" --color red
# raccourci : make show IMG=photo.png
```

`show.py` : reset l'ESP32, attend le marqueur `[PUSH] pret`, trame l'image (paysage 384×168) en
2 plans, l'envoie (en-tête `EPDF` + dimensions + plans) et attend la fin du rendu (~16 s).

Options : `--dither {floyd3,floyd,ordered,none}` (déf. `floyd3` image / `none` texte), `--mode
{cover,fit,stretch}`, `--red-level N`, `--brightness f`, `--invert`, `--color {black,red}`, `--port`.

---

## 2) Afficher en dur (scene.cpp)

Mettre `SHOW_DEFAULT` à `1` dans `include/config.h`, éditer **`src/scene.cpp` → `drawContent()`**, puis
`make upload`.

### Helpers disponibles dans `drawContent()`
| Helper | Usage |
|---|---|
| `printText(x, y, "txt", EPD_BLACK\|EPD_RED, bigFont)` | texte (ligne de base = y) ; `bigFont` true=12pt |
| `drawImageBW(x, y, NOM_black, NOM_W, NOM_H)` | bitmap noir (depuis `images.h`) |
| `drawImageRed(x, y, NOM_red, NOM_W, NOM_H)` | bitmap rouge |
| `drawDigitGrid(GRID_X, GRID_X_COLS, GRID_X_ROWS, x, y, cellPx)` | grille de chiffres (dégradé tramé) |
| `drawDigitGridFill(GRID_X, COLS, ROWS, x, y, w, h)` | **étire** une grille pour remplir une zone |
| `drawDigitGridText("0 1 2\n3 4 5", x, y, cellPx)` | grille depuis une chaîne inline |
| `gfxBlack.drawRect / drawLine / fillCircle / ...` | formes (API Adafruit GFX) ; `gfxRed.*` pour le rouge |

Couleurs : `EPD_WHITE`, `EPD_BLACK`, `EPD_RED`. Écran **384×168**, origine en haut-gauche.

---

## Réglages — `include/config.h`
- **Pins SPI** (`EPD_CS/DC/RST/BUSY/SCK/MOSI`) — câblage de la dalle.
- `SHOW_DEFAULT` — `0` = mode push (déf.) ; `1` = dessine `drawContent()` au boot.
- `EPD_REPL` — `1` = REPL série de diagnostic bas niveau (voir plus bas).
- `USE_WIFI` (+ `WIFI_SSID/PASS`, `NTP_TZ`) — heure NTP (optionnel).
- `GRID_INK_COLOR` / `GRID_RED_FROM` / `GRID_CELL_PX` — rendu des grilles.

---

## Images & dithering — `tools/img2cpp.py`

Convertit une image en bitmaps C (`include/images.h`) pour l'affichage **en dur** :
```bash
python tools/img2cpp.py photo.png                 # 384×168, tramage 3 couleurs (floyd3)
python tools/img2cpp.py logo.png --dither floyd   # N/B seulement
python tools/img2cpp.py img.png --mode cover --red-level 120 --brightness 1.1
```
- `--dither floyd3` : **3 couleurs N/B/R** par diffusion d'erreur — le **rouge sert de ton
  intermédiaire** entre blanc et noir → plus de matière (même sur une photo N/B). Aussi : `floyd`
  (N/B), `ordered` (Bayer), `none` (seuil dur).
- `--mode {cover,fit,stretch}`, `--red-level`, `--brightness`, `--invert`, `--red-sat`.

Le tramage est mutualisé dans `tools/epd_dither.py` (utilisé par `img2cpp.py` ET `show.py`).
Le script affiche les lignes `drawImageBW/Red(...)` à coller dans `drawContent()`.

---

## Grilles de chiffres (dégradés par densité)

Chaque **chiffre 0-9 = une densité** (0 = blanc → 9 = plein), rendue par tramage (Bayer 8×8).

1. Éditer/ajouter un fichier dans `data/grids/` (chiffres 0-9 séparés par des espaces, rangées de
   même largeur). Grilles fournies : `sample`, `ripple`, `radial`, `diamond`, `waves`, `spiral`.
2. `make grids` → génère `include/grids.h` (`GRID_SAMPLE`, `GRID_SAMPLE_COLS`, `GRID_SAMPLE_ROWS`…).
3. Dans `drawContent()` :
   - `drawDigitGrid(GRID_SAMPLE, GRID_SAMPLE_COLS, GRID_SAMPLE_ROWS, x, y, 0);` (auto-fit),
   - ou `drawDigitGridFill(GRID_RIPPLE, GRID_RIPPLE_COLS, GRID_RIPPLE_ROWS, 0, 0, SCREEN_W, SCREEN_H);`
     (étire sur tout l'écran).

---

## Diagnostic — mode REPL

Mettre `EPD_REPL` à `1` (`config.h`) + `make upload`. Le firmware lit des commandes série bas niveau :
`R` (reset), `b` (lire BUSY), `cXX` (commande), `dXX` (donnée), `nXX,KKKK` (envoyer l'octet XX K fois).
Pratique pour sonder une nouvelle dalle (init, refresh, format des données).

---

## Commandes (Makefile)
```bash
make build          # compiler (regénère aussi les grilles)
make upload         # compiler + flasher   (alias: make flash)
make show IMG=x.png # afficher une image via push série (sans reflasher)
make img IMG=x.png  # image -> include/images.h (pour scene.cpp)
make grids          # regénère include/grids.h depuis data/grids/*.txt
make monitor        # logs série (115200)
make nostub         # flash de secours (esptool --no-stub)
make restore        # réécrit l'image de sauvegarde (dump 4 MB, backup/)
make backup         # relit 4 MB de flash -> backup/
make help           # liste toutes les cibles
```

---

## Structure
```
platformio.ini        config build + libs + port
Makefile              raccourcis (build/upload/show/grids/...)
include/
  epd_driver.h        ⚙️ INTERFACE driver (epdInit/epdDisplay/epdSleep/...)
  config.h            ⚙️ pins / flags (SHOW_DEFAULT, EPD_REPL) / Wi-Fi / grille
  display_hal.h       géométrie + plans gfxBlack/gfxRed + showRawPlanes
  images.h            bitmaps (généré par img2cpp.py)
  grids.h             grilles (généré par txt2grid.py)
  scene.h text.h image.h grid.h netclock.h
src/
  main.cpp            setup() + loop() (écoute le push série "EPDF")
  scene.cpp           ★ drawContent() = affichage en dur
  display_hal.cpp     plans GFX + showRawPlanes (push)
  drivers/
    epd2in9b.cpp      driver UC8151 (1 fichier PAR MODÈLE d'écran)
  render/
    text.cpp image.cpp grid.cpp netclock.cpp   helpers de dessin
tools/
  epd_dither.py       conversion image -> plans (dithering 3 couleurs) [partagé]
  img2cpp.py          image -> include/images.h
  show.py             push série d'une image/texte (dynamique)
  txt2grid.py         grille ASCII -> include/grids.h
  flash.sh            flash de secours / restore
data/
  grids/*.txt         grilles de chiffres (sources ASCII)
  images/             images sources
backup/               image de sauvegarde du flash (dump 4 MB)
```

---

## Dépannage
- **`show.py` ne change rien** → l'écran doit être en mode push (`SHOW_DEFAULT=0`) et le port ne doit
  pas être occupé par `make monitor`. `show.py` attend `[PUSH] pret` puis attend la **fin** du rendu
  avant de fermer (fermer le port pendant le refresh le reset et l'annule).
- **Image coupée / bande non dessinée** → question de **résolution** : cette dalle est **168×384**
  (paysage 384×168). Une autre dalle impose d'ajuster `PITCH/ROWS` + la commande `0x61` dans
  `src/drivers/epd2in9b.cpp` et `NATIVE_W/H` dans `include/display_hal.h`.
- **Refresh long (~16 s) qui clignote** → normal (3 couleurs, délais fixes car BUSY non fiable).
- **Flash échoue** (`Failed to write to target RAM` / checksum) → câble/port USB de mauvaise qualité ;
  changer de câble, au pire maintenir **BOOT** au démarrage du flash. `make restore` revient au dump.
- **Réutiliser une autre dalle nue** → beaucoup de dalles e-ink ont besoin d'un circuit d'alimentation
  haute tension (boost VGH/VGL/VCOM) situé sur leur **carte pilote**. Une dalle nue sans ce circuit
  affiche un motif figé indépendant des données (refresh « à vide »).

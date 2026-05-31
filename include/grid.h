#pragma once
// =====================================================================
//  grid — grille de chiffres 0-9 -> dégradé de remplissage (dithering).
//
//  Chaque cellule contient un chiffre 0..9 = densité de remplissage :
//    0 = vide (blanc)  ...  9 = plein (encre).
//  Le rendu utilise un tramage ordonné (matrice de Bayer 8x8) pour
//  simuler des niveaux de gris sur la dalle (qui n'a que b/blanc/rouge).
//
//  Réglages dans config.h : GRID_INK_COLOR, GRID_RED_FROM, GRID_CELL_PX.
// =====================================================================
#include <Arduino.h>

// Dessine une grille déjà parsée (typiquement depuis include/grids.h).
//   cells   : tableau aplati (rows*cols) de valeurs 0..9
//   cols/rows : dimensions
//   x,y     : coin haut-gauche de la grille à l'écran
//   cellPx  : taille d'une cellule en px ; <=0 => auto-fit (selon GRID_CELL_PX
//             puis la place restante à l'écran).
void drawDigitGrid(const uint8_t *cells, uint16_t cols, uint16_t rows,
                   int16_t x, int16_t y, int16_t cellPx = 0);

// Variante : parse une chaîne ASCII multi-ligne à la volée.
// Chiffres 0-9 séparés par des espaces ; un retour à la ligne = nouvelle rangée.
// Pratique pour coller une grille directement dans scene.cpp.
void drawDigitGridText(const char *ascii, int16_t x, int16_t y,
                       int16_t cellPx = 0);

// Étire la grille pour REMPLIR le rectangle (x,y,w,h) — cellules rectangulaires.
// Pratique pour occuper tout l'écran (x=0, y=0, w=SCREEN_W, h=SCREEN_H).
void drawDigitGridFill(const uint8_t *cells, uint16_t cols, uint16_t rows,
                       int16_t x, int16_t y, int16_t w, int16_t h);

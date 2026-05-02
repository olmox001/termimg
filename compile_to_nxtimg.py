#!/usr/bin/env python3
"""
compile_to_nxtimg.py — Converte immagini PNG/JPG in file .nxtimg (testo ANSI)
Uso: python3 compile_to_nxtimg.py input.png output.nxtimg [--width 80] [--height 24]

Output: un file di testo con codici ANSI che può essere:
  - Caricato da termimg.nx in NEXS
  - Montato nel VFS come sd02/logos/nomefile.nxtimg
  - Visualizzato con `termimg nomefile.nxtimg` dalla shell minios
"""

import sys
import os
from PIL import Image

def rgb_to_ansi_256(r, g, b):
    """Converte RGB a codice ANSI 256 colori."""
    if r == g == b:
        if r < 30:
            return 16  # nero
        if r > 225:
            return 231  # bianco
        # scala di grigi 232-255
        gray_idx = int(((r / 255.0) * 23) + 0.5)
        return 232 + gray_idx
    
    # Cubo 6x6x6 (16-231)
    r_idx = int((r / 255.0) * 5)
    g_idx = int((g / 255.0) * 5)
    b_idx = int((b / 255.0) * 5)
    return 16 + r_idx * 36 + g_idx * 6 + b_idx


def image_to_nxtimg(input_path, output_path, term_width=80, term_height=24):
    """
    Converte un'immagine in formato .nxtimg (testo ANSI raw).
    Usa il carattere block inferiore ▀ (U+2580) per raddoppiare la risoluzione verticale.
    """
    try:
        img = Image.open(input_path).convert('RGB')
    except Exception as e:
        print(f"[ERR] Impossibile aprire '{input_path}': {e}")
        return False
    
    # Ridimensiona all'altezza richiesta (term_height - 1 per lasciare spazio alla status bar)
    display_height = (term_height - 1) * 2  # Raddoppia perché usiamo block inferiore
    aspect_ratio = img.width / img.height
    new_width = int(display_height * aspect_ratio)
    new_height = display_height
    
    # Ma limita alla larghezza del terminale
    if new_width > term_width:
        new_width = term_width
        new_height = int(new_width / aspect_ratio)
    
    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    output_lines = []
    
    # Processa ogni riga di caratteri (2 pixel verticali per ogni carattere)
    for char_y in range(term_height - 1):
        line_chars = []
        last_fg = None
        last_bg = None
        
        for char_x in range(term_width):
            img_x = int((char_x / term_width) * img.width)
            img_y_top = int(((char_y * 2) / display_height) * img.height)
            img_y_bottom = int(((char_y * 2 + 1) / display_height) * img.height)
            
            # Clamp
            img_x = min(img_x, img.width - 1)
            img_y_top = min(img_y_top, img.height - 1)
            img_y_bottom = min(img_y_bottom, img.height - 1)
            
            if char_x < new_width:
                top_pixel = img.getpixel((img_x, img_y_top))
                bottom_pixel = img.getpixel((img_x, img_y_bottom))
                
                # Estrai RGB
                top_rgb = top_pixel[:3] if isinstance(top_pixel, tuple) else (top_pixel, top_pixel, top_pixel)
                bottom_rgb = bottom_pixel[:3] if isinstance(bottom_pixel, tuple) else (bottom_pixel, bottom_pixel, bottom_pixel)
                
                fg_code = rgb_to_ansi_256(*top_rgb)
                bg_code = rgb_to_ansi_256(*bottom_rgb)
                
                # Applica codici ANSI solo se cambiano
                if fg_code != last_fg or bg_code != last_bg:
                    line_chars.append(f"\033[38;5;{fg_code}m\033[48;5;{bg_code}m")
                    last_fg = fg_code
                    last_bg = bg_code
                
                line_chars.append("▀")
            else:
                # Padding con spazi se immagine più piccola
                if last_fg is not None:
                    line_chars.append("\033[0m ")
                    last_fg = last_bg = None
                else:
                    line_chars.append(" ")
        
        # Reset a fine riga
        if last_fg is not None:
            line_chars.append("\033[0m")
        
        output_lines.append("".join(line_chars))
    
    # Scrivi il file .nxtimg
    try:
        with open(output_path, "w", encoding="utf-8", newline='\n') as f:
            f.write("\n".join(output_lines))
        print(f"[OK] Compilato: {output_path} ({term_width}x{term_height})")
        return True
    except Exception as e:
        print(f"[ERR] Impossibile scrivere '{output_path}': {e}")
        return False


def main():
    if len(sys.argv) < 3:
        print("Uso: python3 compile_to_nxtimg.py input.png output.nxtimg [--width 80] [--height 24]")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_path = sys.argv[2]
    
    term_width = 80
    term_height = 24
    
    # Parse optional arguments
    for i in range(3, len(sys.argv)):
        if sys.argv[i] == "--width" and i + 1 < len(sys.argv):
            term_width = int(sys.argv[i + 1])
        elif sys.argv[i] == "--height" and i + 1 < len(sys.argv):
            term_height = int(sys.argv[i + 1])
    
    if not os.path.exists(input_path):
        print(f"[ERR] File non trovato: {input_path}")
        sys.exit(1)
    
    success = image_to_nxtimg(input_path, output_path, term_width, term_height)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

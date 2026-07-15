#!/usr/bin/env python3
"""Navegador autonomo da TV por OCR (sem mandar foto manual).
Loop: captura frame -> OCR -> se acha TEXTO-ALVO, manda OK e para;
senao move cursor (setas) e repete. 'Ve' a tela sozinho via visao por texto.

Uso: python3 tv_nav.py "Renan Santos" [device|url] [max_passos] [dry]
  device|url : /dev/video0 (webcam host) ou rtsp://... (celular IP cam)
  dry        : se presente, so imprime OCR, nao manda teclas (teste)

Depende: tools/tv_capture.py, tools/tv_ocr.py, tools/tv_control.py, tesseract.
Limite: app YouTube nativo bloqueia teclado -> so acha alvo se JA visivel
em tela (Inscrições/Recomendados). Pra busca real, abrir YouTube no
navegador da TV (Browser app + URL) onde teclado funciona.
"""
import sys, time, unicodedata
sys.path.insert(0, "/home/rafael/.openclaw/workspace/tools")
from tv_ocr import capture_ocr
from tv_control import send_key

TARGET = sys.argv[1] if len(sys.argv) > 1 else "Renan Santos"
SRC = sys.argv[2] if len(sys.argv) > 2 else "/dev/video0"
MAX = int(sys.argv[3]) if len(sys.argv) > 3 else 40
DRY = "dry" in sys.argv

# varredura zigue-zague: desce, direita, desce, esquerda...
DIRS = ["down", "down", "right", "down", "down", "left"]


def norm(s):
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn").lower()


def main():
    tgt = norm(TARGET)
    print(f"NAV alvo='{TARGET}' src={SRC} max={MAX} dry={DRY}")
    for i in range(MAX):
        txt = capture_ocr(SRC)
        short = " | ".join(l.strip() for l in txt.splitlines() if l.strip())[:120]
        print(f"[{i}] {short}")
        if tgt in norm(txt):
            print(f"ACHEI '{TARGET}' -> OK")
            if not DRY:
                send_key("ok")
            return
        d = DIRS[i % len(DIRS)]
        if not DRY:
            send_key(d)
        time.sleep(1.2)
    print("NAO ACHEI (max passos). Alvo nao visivel na tela atual.")


if __name__ == "__main__":
    main()

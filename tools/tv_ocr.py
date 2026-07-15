#!/usr/bin/env python3
"""Captura frame (webcam ou URL) e roda OCR (tesseract).
'Visao por texto' da tela da TV. Fecha loop: eu leio texto e comando via tv_control.py.
Uso: python3 tv_ocr.py [device|url]
Depende: ffmpeg, tesseract (apt install tesseract-ocr).
"""
import subprocess, sys, os

SRC = sys.argv[1] if len(sys.argv) > 1 else "/dev/video0"
BASE = "/home/rafael/.openclaw/workspace/tools/tv_frame"
FRAME = BASE + ".jpg"


def capture_ocr(src=SRC):
    if src.startswith(("rtsp://", "http://", "https://")):
        inp = ["-i", src, "-rtsp_transport", "tcp"]
    else:
        inp = ["-f", "v4l2", "-i", src]
    subprocess.run(
        ["ffmpeg", "-y"] + inp + ["-frames:v", "1", "-vf", "scale=640:-1", FRAME],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    r = subprocess.run(["tesseract", FRAME, BASE, "-l", "por+eng"],
                       capture_output=True, text=True)
    txt = ""
    if os.path.exists(BASE + ".txt"):
        txt = open(BASE + ".txt").read().strip()
    return txt


if __name__ == "__main__":
    txt = capture_ocr()
    print("FRAME:", FRAME, os.path.getsize(FRAME), "bytes")
    print("OCR TEXT:")
    print(txt if txt else "(vazio - tela escura ou sem texto legivel)")

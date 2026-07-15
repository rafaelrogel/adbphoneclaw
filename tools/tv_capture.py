#!/usr/bin/env python3
"""Captura 1 frame de webcam (/dev/videoN) OU stream de rede (rtsp://, http://).
Uso: python3 tv_capture.py [device|url] [outfile]
Depois tv_ocr.py ou image tool pra 'ver' a tela da TV.
"""
import subprocess, sys, os

SRC = sys.argv[1] if len(sys.argv) > 1 else "/dev/video0"
OUT = sys.argv[2] if len(sys.argv) > 2 else "/home/rafael/.openclaw/workspace/tools/tv_frame.jpg"

if SRC.startswith(("rtsp://", "http://", "https://")):
    inp = ["-i", SRC, "-rtsp_transport", "tcp"]
else:
    inp = ["-f", "v4l2", "-i", SRC]

cmd = ["ffmpeg", "-y"] + inp + ["-frames:v", "1", "-vf", "scale=640:-1", OUT]
r = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
if r.returncode == 0 and os.path.exists(OUT):
    print("CAPTURED", OUT, os.path.getsize(OUT), "bytes")
else:
    print("CAPTURE FAILED (returncode", r.returncode, ")")

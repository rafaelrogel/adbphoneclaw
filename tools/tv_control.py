#!/usr/bin/env python3
"""Controle da TV Toshiba 49V5863G (Vestel) via SmartCenter HTTP API local.
Sem ADB. Liga via WOL, controla via POST em :56789/apps/SmartCenter.
Usa: python3 tv_control.py <cmd> [args]
  wake                 -> WOL (liga TV)
  key <code>           -> envia key code cru
  off                  -> 1012 (power off)
  volup / voldown      -> 1016 / 1017
  mute                 -> 1013
  up / down            -> 1032 / 1033
  chan <1..999>        -> 1000+digito (ex: chan 7 -> 1007)
"""
import socket, sys, time, urllib.request

IP = "192.168.1.210"
MAC = bytes.fromhex("7054b47efbc0")

KEYS = {
    "off": "1012", "volup": "1016", "voldown": "1017",
    "mute": "1013", "up": "1032", "down": "1033",
    "netflix": "1064", "youtube": "1062", "browser": "1065",
    "settings": "1066", "source": "1056", "home": "1048",
    "ok": "1053", "back": "1010", "menu": "1048",
}

def wake():
    pkt = b"\xff" * 6 + MAC * 16
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    for dst in [("192.168.1.255", 9), ("255.255.255.255", 9), (IP, 9)]:
        try:
            s.sendto(pkt, dst)
        except Exception as e:
            print("wol err", dst, e)
    s.close()
    print("WOL sent ->", IP)

def openp(p, t=1.0):
    s = socket.socket(); s.settimeout(t)
    try:
        s.connect((IP, p)); return True
    except Exception:
        return False
    finally:
        s.close()

def send_key(code, wait=0.3):
    if not openp(56789):
        print("TV not reachable on 56789 (awake first? try: wake)")
        return False
    url = f"http://{IP}:56789/apps/SmartCenter"
    body = f"<?xml version='1.0' ?><remote><key code='{code}'/></remote>"
    req = urllib.request.Request(url, data=body.encode("iso-8859-1"), method="POST")
    req.add_header("Content-Type", "text/plain; charset=ISO-8859-1")
    req.add_header("application_name", "vestel smart center")
    req.add_header("Connection", "keep-alive")
    try:
        r = urllib.request.urlopen(req, timeout=6)
        print(f"key {code} -> HTTP {r.status}")
        return True
    except Exception as e:
        print("send_key failed:", e)
        return False

def keyboard(text, wait=0.5):
    if not openp(56789):
        print("TV not reachable on 56789 (awake first? try: wake)")
        return False
    url = f"http://{IP}:56789/apps/SmartCenter"
    body = f"<?xml version='1.0' ?><keyboard>{text}</keyboard>"
    req = urllib.request.Request(url, data=body.encode("iso-8859-1"), method="POST")
    req.add_header("Content-Type", "text/plain; charset=ISO-8859-1")
    req.add_header("application_name", "vestel smart center")
    req.add_header("Connection", "keep-alive")
    try:
        r = urllib.request.urlopen(req, timeout=6)
        print(f"keyboard '{text}' -> HTTP {r.status}")
        return True
    except Exception as e:
        print("keyboard failed:", e)
        return False

def chan(n):
    for d in str(n):
        send_key(str(1000 + int(d)))

def main():
    if len(sys.argv) < 2:
        print(__doc__); return
    cmd = sys.argv[1].lower()
    if cmd == "wake":
        wake()
    elif cmd == "key":
        send_key(sys.argv[2])
    elif cmd == "chan":
        chan(sys.argv[2])
    elif cmd == "kb":
        keyboard(sys.argv[2])
    elif cmd in KEYS:
        send_key(KEYS[cmd])
    else:
        print("unknown:", cmd); print(__doc__)

if __name__ == "__main__":
    main()

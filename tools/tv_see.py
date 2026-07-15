#!/usr/bin/env python3
"""Ve TV de verdade via Ollama vision local (moondream/llava).
Captura frame (webcam ou URL) e manda pra modelo vision local.
Retorna descricao da tela. Fecha loop sem crédito OpenRouter e sem foto manual.
Uso: python3 tv_see.py [device|url] [prompt]
Depende: ollama rodando, modelo vision puxado (ollama pull moondream).
"""
import sys, base64, json, urllib.request

sys.path.insert(0, "/home/rafael/.openclaw/workspace/tools")
from tv_ocr import capture_ocr, FRAME

SRC = sys.argv[1] if len(sys.argv) > 1 else "/dev/video0"
PROMPT = sys.argv[2] if len(sys.argv) > 2 else \
    "Describe this TV screen briefly: which app, visible text/menus, what is playing. Be concise."

capture_ocr(SRC)
b64 = base64.b64encode(open(FRAME, "rb").read()).decode()
payload = json.dumps({"model": "moondream", "prompt": PROMPT, "images": [b64]}).encode()
req = urllib.request.Request(
    "http://localhost:11434/api/generate",
    data=payload, headers={"Content-Type": "application/json"},
)
r = urllib.request.urlopen(req)
out = ""
for line in r:
    try:
        out += json.loads(line).get("response", "")
    except Exception:
        pass
print(out or "(sem resposta do modelo)")

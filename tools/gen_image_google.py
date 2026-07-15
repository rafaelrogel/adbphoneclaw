#!/usr/bin/env python3
"""Gera imagem via Google AI Studio (Gemini image) usando chaves em arquivos seguros.
Uso: python3 gen_image_google.py "<prompt>" <outfile>
Tenta todas as chaves x todos os modelos ate um funcionar. Nao imprime as chaves.
"""
import sys, os, json, base64, urllib.request, urllib.error

KEYFILES = [
    "/home/rafael/.openclaw/secrets/google-ai-studio.key",
    "/home/rafael/.openclaw/secrets/google-ai-studio-2.key",
]
MODELS = [
    "gemini-3.1-flash-image-preview",
    "gemini-3-pro-image-preview",
    "gemini-2.5-flash-preview-image-generation",
    "gemini-2.0-flash-preview-image-generation",
]


def gen(prompt, out, model, key):
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/{model}"
           f":generateContent?key={key}")
    cfg = {"responseModalities": ["IMAGE"]}
    body = json.dumps({
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": cfg,
    }).encode()
    req = urllib.request.Request(url, data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        r = urllib.request.urlopen(req, timeout=180)
        data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}: {e.read().decode()[:200]}"
    except Exception as e:
        return None, str(e)[:200]
    try:
        parts = data["candidates"][0]["content"]["parts"]
        for p in parts:
            if "inlineData" in p:
                b64 = p["inlineData"]["data"]
                mime = p["inlineData"].get("mimeType", "image/png")
                raw = base64.b64decode(b64)
                ext = "png" if "png" in mime else ("jpg" if "jpeg" in mime else "png")
                base, _ = os.path.splitext(out)
                final = base + "." + ext
                with open(final, "wb") as f:
                    f.write(raw)
                return final, None
    except Exception as e:
        return None, f"parse: {e} | {str(data)[:150]}"
    return None, "sem imagem: " + str(data)[:150]


if __name__ == "__main__":
    prompt = sys.argv[1]
    out = sys.argv[2]
    for kf in KEYFILES:
        if not os.path.exists(kf):
            continue
        key = open(kf).read().strip()
        print("== chave:", kf.split("/")[-1])
        for m in MODELS:
            print("  tentando", m, "...")
            path, err = gen(prompt, out, m, key)
            if path:
                print("OK", m, "->", path, os.path.getsize(path), "bytes")
                break
            else:
                print("    falhou:", err)
        if path:
            break
    else:
        print("TODOS FALHARAM (todas chaves)")
        sys.exit(1)

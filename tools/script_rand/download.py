#!/usr/bin/env python3
import json, os, urllib.request, concurrent.futures, csv, sys

BASE = "https://script-randomizador.vercel.app"
ROOT = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(ROOT, "assets")
MSGS = os.path.join(ROOT, "messages")
os.makedirs(ASSETS, exist_ok=True)
os.makedirs(MSGS, exist_ok=True)

with open(os.path.join(ROOT, "manifest.json"), encoding="utf-8") as f:
    data = json.load(f)

items = data["items"]

def pad(n):
    return f"{int(n):04d}"

def fetch(it):
    fn = it["file"]
    url = f"{BASE}/galeria/{urllib.parse.quote(fn)}"
    dst = os.path.join(ASSETS, fn)
    try:
        if os.path.exists(dst) and os.path.getsize(dst) > 0:
            return fn, "skip"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as r, open(dst, "wb") as w:
            w.write(r.read())
        return fn, "ok"
    except Exception as e:
        return fn, f"ERR:{e}"

import urllib.parse

# 1) download all assets concurrently
results = {}
with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
    for fn, st in ex.map(fetch, items):
        results[fn] = st

# 2) write per-number message files + structured posts
posts = []
for it in items:
    n = it["n"]
    legenda = it.get("legenda", "")
    mtxt = os.path.join(MSGS, f"{pad(n)}.txt")
    with open(mtxt, "w", encoding="utf-8") as w:
        w.write(legenda)
    posts.append({
        "n": n,
        "estilo": it.get("estilo"),
        "file": it["file"],
        "asset_path": os.path.join("assets", it["file"]),
        "legenda": legenda,
    })

# posts.json (ordered by n)
with open(os.path.join(ROOT, "posts.json"), "w", encoding="utf-8") as f:
    json.dump({"total": len(posts), "counts": data["counts"], "posts": posts}, f, ensure_ascii=False, indent=2)

# posts.csv
with open(os.path.join(ROOT, "posts.csv"), "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f)
    w.writerow(["n", "estilo", "file", "asset_path", "legenda"])
    for p in posts:
        w.writerow([p["n"], p["estilo"], p["file"], p["asset_path"], p["legenda"]])

ok = sum(1 for v in results.values() if v == "ok")
skip = sum(1 for v in results.values() if v == "skip")
err = [f"{k}:{v}" for k, v in results.items() if v.startswith("ERR")]
print(f"assets: ok={ok} skip={skip} err={len(err)}")
if err:
    print("ERRORS:")
    for e in err[:20]:
        print(" ", e)
print(f"messages: {len(posts)} arquivos em messages/")
print(f"posts.json + posts.csv escritos")

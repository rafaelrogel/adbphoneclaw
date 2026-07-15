#!/usr/bin/env python3
"""
Agenda 400 posts no Bluesky via Postiz public API.
- 1 post/dia, ordem 1..400, 400 dias total.
- Resumable: state file evita duplicar.
- Auth: POSTIZ_API_KEY (Bearer).
"""
import os, sys, json, time, datetime, mimetypes
import urllib.request, urllib.error

BASE = "https://postiz.cortespoliticos.online/api/public/v1"
ROOT = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(ROOT, "assets")
STATE = os.path.join(ROOT, "schedule_state.json")

START_HOUR_UTC = 9  # 09:00 UTC por dia

def load_state():
    if os.path.exists(STATE):
        try:
            return json.load(open(STATE, encoding="utf-8"))
        except Exception:
            pass
    return {"media": {}, "done": []}

def save_state(s):
    tmp = STATE + ".tmp"
    json.dump(s, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    os.replace(tmp, STATE)

def api(key, method, path, data=None, files=None):
    url = BASE + path
    headers = {"Authorization": key}
    if files is None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(data).encode() if data is not None else None
    else:
        # multipart
        boundary = "----a1postizboundary"
        parts = []
        for fld, val in (data or {}).items():
            parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{fld}\"\r\n\r\n{val}\r\n".encode())
        for fld, fpath in files.items():
            mt = mimetypes.guess_type(fpath)[0] or "application/octet-stream"
            parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{fld}\"; filename=\"{os.path.basename(fpath)}\"\r\nContent-Type: {mt}\r\n\r\n".encode())
            parts.append(open(fpath, "rb").read())
            parts.append(b"\r\n")
        parts.append(f"--{boundary}--\r\n".encode())
        body = b"".join(parts)
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read().decode()
            return r.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="ignore")
        return e.code, {"error": raw}

def main():
    key = os.environ.get("POSTIZ_API_KEY")
    if not key:
        print("ERRO: defina POSTIZ_API_KEY"); sys.exit(1)
    st = load_state()
    media_cache = st.setdefault("media", {})
    done = set(st.get("done", []))

    # 1) integration id (bluesky)
    code, integ = api(key, "GET", "/integrations")
    if code != 200:
        print(f"ERRO listar integrations: {code} {integ}"); sys.exit(1)
    items = integ if isinstance(integ, list) else integ.get("integrations", [])
    bs = None
    for it in items:
        if it.get("identifier") == "bluesky" or "bluesky" in str(it.get("identifier","")).lower():
            bs = it; break
    if not bs:
        print("Bluesky nao encontrado. integrations:", [i.get("identifier") for i in items]); sys.exit(1)
    bs_id = bs["id"]

    # load posts
    posts = json.load(open(os.path.join(ROOT, "posts.json"), encoding="utf-8"))["posts"]
    posts_sorted = sorted(posts, key=lambda p: p["n"])

    now = datetime.datetime.now(datetime.timezone.utc)
    start = (now + datetime.timedelta(days=1)).replace(hour=START_HOUR_UTC, minute=0, second=0, microsecond=0)

    total = len(posts_sorted)
    print(f"[init] key ok. Bluesky={bs_id} | {total} posts | inicio {start.isoformat()}", flush=True)
    for idx, p in enumerate(posts_sorted, 1):
        n = p["n"]
        if n in done:
            print(f"[{idx}/{total}] #{n} skip (ja feito)"); continue
        fpath = os.path.join(ROOT, p["asset_path"])
        # upload media (cached)
        rel = p["file"]
        if rel in media_cache:
            mid, mpath = media_cache[rel]["id"], media_cache[rel]["path"]
        else:
            up = None
            for attempt in range(6):
                code, up = api(key, "POST", "/upload", files={"file": fpath})
                if code in (200, 201):
                    break
                print(f"[{idx}/{total}] #{n} upload retry {code} (tent {attempt+1})", flush=True)
                time.sleep(5 * (attempt + 1))
            if not up or code not in (200, 201):
                print(f"[{idx}/{total}] #{n} ERRO upload {code} {up}", flush=True)
                time.sleep(2)
                continue
            mid = up.get("id") or up.get("path")
            mpath = up.get("path") or up.get("filePath") or rel
            media_cache[rel] = {"id": mid, "path": mpath}
            save_state(st)
        # schedule date
        dt = start + datetime.timedelta(days=(n-1))
        iso = dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        payload = {
            "type": "schedule",
            "shortLink": False,
            "date": iso,
            "tags": [],
            "posts": [{
                "integration": {"id": bs_id},
                "value": [{"content": p["legenda"], "image": [{"id": mid, "path": mpath}]}],
                "settings": {"__type": "bluesky"},
            }],
        }
        created = False
        for attempt in range(8):
            code, resp = api(key, "POST", "/posts", data=payload)
            if code in (200, 201):
                created = True
                break
            print(f"[{idx}/{total}] #{n} criar retry {code} (tent {attempt+1}) {resp}", flush=True)
            time.sleep(8 * (attempt + 1))
        if not created:
            print(f"[{idx}/{total}] #{n} ERRO criar {code} {resp}", flush=True)
            time.sleep(2)
            continue
        done.add(n)
        st["done"] = sorted(done)
        save_state(st)
        print(f"[{idx}/{total}] #{n} OK -> {iso}")
        time.sleep(0.3)

    print(f"FIM. {len(done)}/{total} agendados.")

if __name__ == "__main__":
    main()

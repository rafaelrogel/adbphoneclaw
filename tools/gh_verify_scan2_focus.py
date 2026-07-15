#!/usr/bin/env python3
"""Focused verify scan2: HIGH-RISK + AI-MODEL-API. Concurrent (6 workers).
API autenticada + resume. Masks ALL secrets. NEVER uses/tests.
"""
import json, time, re, os, requests, base64
from concurrent.futures import ThreadPoolExecutor, as_completed

API = "https://api.github.com/repos/{repo}/contents/{path}"
OUT = "tools/gh_verify_scan2_focus_verdicts.json"
FOCUS = {"PEMkey", "AWS", "FB", "Stripe", "OpenAI", "Google",
         "Google2", "NVidia", "Anthropic"}
WORKERS = 6

PAT = {
    "AWS":       re.compile(r"AKIA[0-9A-Z]{16}"),
    "FB":        re.compile(r"EAACEdEose0cBA[0-9A-Za-z]+"),
    "Stripe":    re.compile(r"sk_live_[0-9A-Za-z]{24,}"),
    "OpenAI":    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    "Anthropic": re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}"),
    "Google":    re.compile(r"AIza[0-9A-Za-z_\-]{35}"),
    "Google2":   re.compile(r"ya29\.[0-9A-Za-z_\-]{30,}"),
    "NVidia":    re.compile(r"nvapi-[0-9A-Za-z]{32,}"),
    "PEMkey":    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
}
PLACEHOLDER = re.compile(
    r"(your_|example|xxxx|changeme|replace|insert|placeholder|fake|dummy|"
    r"<your|todo|redacted|\*{4,}|abcdef|test_|yourkey|paste|here|sample|"
    r"dummyval|your-api|your-secret|xxxxxxxx|00000000|key_here|add_your|"
    r"put_your|remove_this|replace_this|your_token|your-secret-key|"
    r"your_api_key|secret_key_here|api_key_here|yourkeyhere|xxxxxxxxxxxx)", re.I)

TOKEN = os.environ.get("GITHUB_PAT")
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json"} if TOKEN else {}

def mask(s):
    if len(s) <= 8: return s[:2] + "***"
    return s[:6] + "***" + s[-2:]

def fetch_and_classify(item):
    repo, path, label = item["repo"], item["path"], item["label"]
    try:
        r = requests.get(API.format(repo=repo, path=path), headers=HEADERS, timeout=30)
        if r.status_code == 200:
            try:
                content = base64.b64decode(r.json()["content"]).decode("utf-8", "replace")
            except Exception:
                return {"repo": repo, "path": path, "label": label,
                        "verdict": "FETCH_ERR", "code": 500}
            rx = PAT.get(label)
            if not rx:
                return {"repo": repo, "path": path, "label": label,
                        "verdict": "NO_MATCH", "secret": None}
            m = rx.search(content)
            if not m:
                return {"repo": repo, "path": path, "label": label,
                        "verdict": "NO_MATCH", "secret": None}
            val = m.group(0)
            ctx = ""
            for line in content.splitlines():
                if val[:8] in line:
                    ctx = line; break
            if PLACEHOLDER.search(ctx) or PLACEHOLDER.search(content[:1500]):
                return {"repo": repo, "path": path, "label": label,
                        "verdict": "FAKE", "secret": mask(val)}
            if len(val) < 12:
                return {"repo": repo, "path": path, "label": label,
                        "verdict": "FAKE", "secret": mask(val)}
            return {"repo": repo, "path": path, "label": label,
                    "verdict": "REAL", "secret": mask(val)}
        return {"repo": repo, "path": path, "label": label,
                "verdict": "FETCH_ERR", "code": r.status_code}
    except Exception as e:
        return {"repo": repo, "path": path, "label": label,
                "verdict": "ERR", "msg": str(e)[:80]}

def main():
    if not TOKEN:
        print("ERRO: GITHUB_PAT nao exportado"); return
    data = json.load(open("tools/gh_secret_scan2.json"))
    data = [d for d in data if d["label"] in FOCUS]
    done = {}
    try:
        for v in json.load(open(OUT)):
            done[v["repo"] + "|" + v["path"]] = v
    except Exception:
        pass
    pending = [d for d in data if (d["repo"] + "|" + d["path"]) not in done]
    print(f"foco {len(data)} | feitos {len(done)} | pendentes {len(pending)}", flush=True)
    results = list(done.values())
    real_count = sum(1 for v in results if v["verdict"] == "REAL")
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(fetch_and_classify, d): d for d in pending}
        for i, fut in enumerate(as_completed(futs), 1):
            v = fut.result()
            results.append(v); done[v["repo"] + "|" + v["path"]] = v
            if v["verdict"] == "REAL": real_count += 1
            if i % 50 == 0:
                json.dump(results, open(OUT, "w"), indent=2)
                print(f"  [{i}/{len(pending)}] reals={real_count}", flush=True)
    json.dump(results, open(OUT, "w"), indent=2)
    reals = [v for v in results if v["verdict"] == "REAL"]
    print(f"\n=== REAL: {len(reals)} ===", flush=True)
    for v in reals:
        print(f"  {v['label']:9} {v['repo']:42} {v['path']:28} {v.get('secret')}", flush=True)

if __name__ == "__main__":
    main()

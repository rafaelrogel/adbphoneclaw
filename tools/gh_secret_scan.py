#!/usr/bin/env python3
"""GitHub public code search for leaked secrets — responsible disclosure prep.
Finds leaked keys in PUBLIC repos only. Never uses/tests the keys.
Outputs: repo owner, repo, file path, pattern, masked snippet.
"""
import os, sys, time, json
import requests

TOKEN = os.environ.get("GITHUB_PAT")
if not TOKEN:
    print("ERRO: GITHUB_PAT faltando"); sys.exit(1)

# (label, query) — queries go to /search/code
PATTERNS = [
    ("AWS",      "AKIA filename:.env"),
    ("GitHubPAT","ghp_ in:file"),
    ("Slack",    "xoxb- in:file"),
    ("Google",   "AIza in:file"),
    ("Stripe",   "sk_live_ in:file"),
    ("PEMkey",   '"BEGIN PRIVATE KEY" in:file'),
    ("OpenAI",   "sk- in:file filename:.env"),
]

HEADERS = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json"}
API = "https://api.github.com/search/code"
MAX_PER_PATTERN = 20  # cap to stay polite on rate limit

def search(label, q):
    out = []
    page = 1
    while len(out) < MAX_PER_PATTERN and page <= 3:
        r = requests.get(API, headers=HEADERS, params={"q": q, "per_page": 100, "page": page}, timeout=30)
        if r.status_code == 403 or r.status_code == 429:
            print(f"[{label}] rate limit {r.status_code}; sleep 60", flush=True)
            time.sleep(60); continue
        if r.status_code != 200:
            print(f"[{label}] HTTP {r.status_code}: {r.text[:200]}", flush=True)
            break
        data = r.json()
        for it in data.get("items", []):
            repo = it["repository"]["full_name"]
            path = it["path"]
            out.append({"label": label, "repo": repo, "path": path, "query": q})
            if len(out) >= MAX_PER_PATTERN:
                break
        if not data.get("items"): break
        page += 1
        time.sleep(2)
    return out

def main():
    results = []
    for label, q in PATTERNS:
        print(f"[buscar] {label}: {q}", flush=True)
        results.extend(search(label, q))
        time.sleep(3)
    # dedupe by repo
    seen = {}
    for r in results:
        seen.setdefault(r["repo"], r)
    print(f"\n=== {len(results)} matches, {len(seen)} repos unicos ===")
    for repo, r in sorted(seen.items()):
        print(f"{r['label']:10} {repo:45} {r['path']}")
    # save
    with open("tools/gh_secret_scan_results.json", "w") as f:
        json.dump(list(seen.values()), f, indent=2)
    print(f"\nsalvo tools/gh_secret_scan_results.json ({len(seen)} repos)")

if __name__ == "__main__":
    main()

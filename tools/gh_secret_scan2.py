#!/usr/bin/env python3
"""Second-pass GitHub secret scan. Valid PAT (30 req/min).
Strategy: literal prefixes (code search is NOT regex) + deep pagination
(pages 1..MAX) to find repos beyond scan1's first 100. Dedupe vs scan1.
NEVER uses/tests keys.
"""
import json, time, os, requests

TOKEN = os.environ.get("GITHUB_PAT")
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json"} if TOKEN else {}
SEARCH = "https://api.github.com/search/code"
# literal prefixes (GitHub code search matches substrings, no regex)
PATTERNS = {
    "AWS":      "AKIA",
    "GitHubPAT":"ghp_",
    "GitHubPAT2":"gho_",
    "GitHubPAT3":"ghu_",
    "GitHubPAT4":"ghs_",
    "GitHubPAT5":"ghr_",
    "Slack":    "xoxb-",
    "Slack2":   "xoxp-",
    "Google":   "AIza",
    "Google2":  "ya29.",
    "Stripe":   "sk_live_",
    "OpenAI":   "sk-",
    "GitLab":   "glpat-",
    "NVidia":   "nvapi-",
    "FB":       "EAACEdEose0cBA",
    "PEMkey":   "BEGIN PRIVATE KEY",
}
MAX_PAGES = 10
PER = 100
DELAY = 2  # 30 req/min budget

def main():
    old = set()
    try:
        for r in json.load(open("tools/gh_secret_scan_results.json")):
            old.add(r["repo"] + "|" + r["path"])
    except Exception:
        pass
    results = []
    for label, pat in PATTERNS.items():
        for page in range(1, MAX_PAGES + 1):
            q = f"{pat} in:file"
            try:
                r = requests.get(SEARCH, params={"q": q, "per_page": PER, "page": page},
                                  headers=HEADERS, timeout=30)
                if r.status_code == 403:
                    print(f"[{label}] 403 RATE -> sleep 60", flush=True)
                    time.sleep(60); continue
                if r.status_code != 200:
                    print(f"[{label} p{page}] HTTP {r.status_code} {r.text[:120]}", flush=True)
                    break
                items = r.json().get("items", [])
                if not items:
                    break
                new = 0
                for it in items:
                    repo = it["repository"]["full_name"]
                    path = it["path"]
                    key = repo + "|" + path
                    if key in old:
                        continue
                    old.add(key)
                    results.append({"repo": repo, "path": path, "label": label,
                                    "url": it["html_url"]})
                    new += 1
                print(f"[{label} p{page}] +{new} (total acum {len(results)})", flush=True)
                if len(items) < PER:
                    break
            except Exception as e:
                print(f"[{label} p{page}] ERR {e}", flush=True)
                break
            time.sleep(DELAY)
    # dedupe final
    seen = set(); uniq = []
    for x in results:
        k = x["repo"] + "|" + x["path"]
        if k in seen: continue
        seen.add(k); uniq.append(x)
    json.dump(uniq, open("tools/gh_secret_scan2.json", "w"), indent=2)
    print(f"\nNOVOS unicos: {len(uniq)} -> tools/gh_secret_scan2.json", flush=True)

if __name__ == "__main__":
    main()

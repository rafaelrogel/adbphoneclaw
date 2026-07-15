#!/usr/bin/env python3
"""Verify candidates via raw.githubusercontent.com (no token needed for public repos).
Classifies real leaked secret vs placeholder/example. Masks secrets. Never uses/tests.
"""
import json, time, re, requests

RAW = "https://raw.githubusercontent.com/{repo}/{branch}/{path}"
PATTERNS = {
    "AWS":      re.compile(r"AKIA[0-9A-Z]{16}"),
    "GitHubPAT":re.compile(r"ghp_[0-9A-Za-z]{36}"),
    "Slack":    re.compile(r"xoxb-[0-9]{10,}-[0-9]{10,}-[A-Za-z0-9]{20,}"),
    "Google":   re.compile(r"AIza[0-9A-Za-z_\-]{35}"),
    "Stripe":   re.compile(r"sk_live_[0-9A-Za-z]{24,}"),
    "PEMkey":   re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "OpenAI":   re.compile(r"sk-[A-Za-z0-9]{20,}"),
}
# weak matches we ignore (clearly not a real key)
PLACEHOLDER = re.compile(
    r"(your_|example|xxxx|changeme|replace|insert|placeholder|fake|dummy|"
    r"<your|todo|redacted|\*{4,}|abcdef|test_|yourkey|paste|here|sample|"
    r"dummyval|your-api|your-secret|xxxxxxxx|00000000|key_here|add_your|"
    r"put_your|remove_this|replace_this)", re.I)

def mask(s):
    if len(s) <= 8: return s[:2] + "***"
    return s[:6] + "***" + s[-2:]

def fetch(repo, path):
    for branch in ("main", "master"):
        r = requests.get(RAW.format(repo=repo, branch=branch, path=path), timeout=30)
        if r.status_code == 200:
            return r.text, 200, branch
        if r.status_code == 404:
            continue
        return None, r.status_code, branch
    return None, 404, "main"

def classify(label, content):
    m = PATTERNS[label].search(content)
    if not m:
        return "NO_MATCH", None
    val = m.group(0)
    # find the line containing it for context
    for line in content.splitlines():
        if val[:8] in line:
            ctx = line
            break
    else:
        ctx = ""
    if PLACEHOLDER.search(ctx) or PLACEHOLDER.search(content[:1500]):
        return "FAKE", mask(val)
    if len(val) < 12:
        return "FAKE", mask(val)
    return "REAL", mask(val)

def main():
    data = json.load(open("tools/gh_secret_scan_results.json"))
    verdicts = []
    for r in data:
        repo, path, label = r["repo"], r["path"], r["label"]
        content, code, branch = fetch(repo, path)
        if content is None:
            verdicts.append({"repo": repo, "path": path, "label": label,
                             "verdict": "FETCH_ERR", "code": code})
            print(f"[{'ERR'+str(code):9}] {label:9} {repo:42} {path}", flush=True)
            time.sleep(0.6); continue
        v, secret = classify(label, content)
        verdicts.append({"repo": repo, "path": path, "label": label,
                         "verdict": v, "secret": secret, "branch": branch})
        print(f"[{v:9}] {label:9} {repo:42} {path:30} {secret or ''}", flush=True)
        time.sleep(0.6)
    reals = [v for v in verdicts if v["verdict"] == "REAL"]
    print(f"\n=== REAL candidates: {len(reals)} ===")
    for v in reals:
        print(f"  {v['label']:9} {v['repo']}  {v['path']}  ({v.get('secret')})")
    json.dump(verdicts, open("tools/gh_verify_verdicts.json", "w"), indent=2)
    print(f"\nsalvo tools/gh_verify_verdicts.json")

if __name__ == "__main__":
    main()

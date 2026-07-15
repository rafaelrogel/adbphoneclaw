#!/usr/bin/env python3
"""Verify each candidate: real leaked secret or placeholder/example.
Fetches file via GitHub API, masks secrets, classifies.
NEVER prints full secret. NEVER uses/tests key.
"""
import os, sys, json, time, re, base64
import requests

TOKEN = os.environ.get("GITHUB_PAT")
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json"}
API = "https://api.github.com/repos"

PATTERNS = {
    "AWS":      re.compile(r"AKIA[0-9A-Z]{16}"),
    "GitHubPAT":re.compile(r"ghp_[0-9A-Za-z]{36}"),
    "Slack":    re.compile(r"xoxb-[0-9]{10,}-[0-9]{10,}-[A-Za-z0-9]{20,}"),
    "Google":   re.compile(r"AIza[0-9A-Za-z_\-]{35}"),
    "Stripe":   re.compile(r"sk_live_[0-9A-Za-z]{24,}"),
    "PEMkey":   re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "OpenAI":   re.compile(r"sk-[A-Za-z0-9]{20,}"),
}
PLACEHOLDER = re.compile(
    r"(your_|example|example\.|xxxx|changeme|replace|insert|placeholder|"
    r"fake|dummy|<your|todo|redacted|\*{4,}|xxxxxx|00000000|abcdef|test_|"
    r"your-key|yourkey|paste|here|sample|dummyval)", re.I)

def mask(s):
    if len(s) <= 8: return s[:2] + "***"
    return s[:6] + "***" + s[-2:]

def fetch(repo, path):
    r = requests.get(f"{API}/{repo}/contents/{path}", headers=HEADERS, timeout=30)
    if r.status_code != 200:
        return None, r.status_code
    j = r.json()
    if isinstance(j, list):  # dir
        return None, 300
    content = base64.b64decode(j.get("content", "")).decode("utf-8", "replace")
    return content, 200

def classify(label, content):
    m = PATTERNS[label].search(content)
    if not m:
        return "NO_MATCH", None
    val = m.group(0)
    # context line
    line = [l for l in content.splitlines() if m.group(0)[:8] in l or val[:8] in l]
    ctx = line[0] if line else ""
    if PLACEHOLDER.search(ctx) or PLACEHOLDER.search(content[:2000]):
        return "FAKE", mask(val)
    if len(val) < 10:
        return "FAKE", mask(val)
    return "REAL", mask(val)

def main():
    data = json.load(open("tools/gh_secret_scan_results.json"))
    verdicts = []
    for r in data:
        repo, path, label = r["repo"], r["path"], r["label"]
        content, code = fetch(repo, path)
        if content is None:
            verdicts.append({"repo": repo, "path": path, "label": label,
                             "verdict": "FETCH_ERR", "code": code, "secret": None})
            time.sleep(1); continue
        v, secret = classify(label, content)
        verdicts.append({"repo": repo, "path": path, "label": label,
                         "verdict": v, "secret": secret})
        print(f"[{v:9}] {label:9} {repo:42} {path:32} {secret or ''}", flush=True)
        time.sleep(1.2)
    reals = [v for v in verdicts if v["verdict"] == "REAL"]
    print(f"\n=== REAL candidates: {len(reals)} ===")
    for v in reals:
        print(f"  {v['label']:9} {v['repo']}  {v['path']}  ({v['secret']})")
    json.dump(verdicts, open("tools/gh_verify_verdicts.json", "w"), indent=2)
    print(f"\nsalvo tools/gh_verify_verdicts.json")

if __name__ == "__main__":
    main()

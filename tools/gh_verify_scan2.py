#!/usr/bin/env python3
"""Verify scan2 candidates via raw.githubusercontent.com. Classify REAL vs FAKE.
Masks ALL secrets. NEVER uses/tests. Focus: high-signal labels first.
"""
import json, time, re, requests

RAW = "https://raw.githubusercontent.com/{repo}/{branch}/{path}"
VERIFY_LABELS = {"PEMkey", "AWS", "GitHubPAT", "GitHubPAT2", "GitHubPAT3",
                 "GitHubPAT4", "GitHubPAT5", "FB", "Slack", "OpenAI",
                 "Google", "Google2", "Stripe", "GitLab", "NVidia"}

PAT = {
    "AWS":       re.compile(r"AKIA[0-9A-Z]{16}"),
    "GitHubPAT": re.compile(r"ghp_[0-9A-Za-z]{36}"),
    "GitHubPAT2":re.compile(r"gho_[0-9A-Za-z]{36}"),
    "GitHubPAT3":re.compile(r"ghu_[0-9A-Za-z]{36}"),
    "GitHubPAT4":re.compile(r"ghs_[0-9A-Za-z]{36}"),
    "GitHubPAT5":re.compile(r"ghr_[0-9A-Za-z]{36}"),
    "Slack":     re.compile(r"xox[bap]-[0-9]{8,}-[0-9]{8,}-[A-Za-z0-9]{20,}"),
    "OpenAI":    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    "Google":    re.compile(r"AIza[0-9A-Za-z_\-]{35}"),
    "Google2":   re.compile(r"ya29\.[0-9A-Za-z_\-]{30,}"),
    "Stripe":    re.compile(r"sk_live_[0-9A-Za-z]{24,}"),
    "GitLab":    re.compile(r"glpat-[0-9A-Za-z_\-]{20,}"),
    "NVidia":    re.compile(r"nvapi-[0-9A-Za-z]{32,}"),
    "FB":        re.compile(r"EAACEdEose0cBA[0-9A-Za-z]+"),
    "PEMkey":    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
}
PLACEHOLDER = re.compile(
    r"(your_|example|xxxx|changeme|replace|insert|placeholder|fake|dummy|"
    r"<your|todo|redacted|\*{4,}|abcdef|test_|yourkey|paste|here|sample|"
    r"dummyval|your-api|your-secret|xxxxxxxx|00000000|key_here|add_your|"
    r"put_your|remove_this|replace_this|your_token|your-secret-key)", re.I)

def mask(s):
    if len(s) <= 8: return s[:2] + "***"
    return s[:6] + "***" + s[-2:]

def fetch(repo, path):
    for branch in ("main", "master"):
        r = requests.get(RAW.format(repo=repo, branch=branch, path=path), timeout=30)
        if r.status_code == 200:
            return r.text, 200
        if r.status_code == 404:
            continue
        if r.status_code == 429:
            time.sleep(10); continue
        return None, r.status_code
    return None, 404

def classify(label, content):
    rx = PAT.get(label, PAT.get(label.rstrip("0123456789"), None))
    if rx is None:
        return "NO_MATCH", None
    m = rx.search(content)
    if not m:
        return "NO_MATCH", None
    val = m.group(0)
    for line in content.splitlines():
        if val[:8] in line:
            ctx = line; break
    else:
        ctx = ""
    if PLACEHOLDER.search(ctx) or PLACEHOLDER.search(content[:1500]):
        return "FAKE", mask(val)
    if len(val) < 12:
        return "FAKE", mask(val)
    return "REAL", mask(val)

def main():
    data = json.load(open("tools/gh_secret_scan2.json"))
    data = [d for d in data if d["label"] in VERIFY_LABELS]
    print(f"verificando {len(data)} candidatos...", flush=True)
    verdicts = []
    real_count = 0
    for i, r in enumerate(data):
        repo, path, label = r["repo"], r["path"], r["label"]
        content, code = fetch(repo, path)
        if content is None:
            verdicts.append({"repo": repo, "path": path, "label": label,
                             "verdict": "FETCH_ERR", "code": code})
            time.sleep(0.5); continue
        v, secret = classify(label, content)
        if v == "REAL": real_count += 1
        verdicts.append({"repo": repo, "path": path, "label": label,
                         "verdict": v, "secret": secret})
        if (i+1) % 50 == 0:
            print(f"  [{i+1}/{len(data)}] reals_ate_agora={real_count}", flush=True)
        time.sleep(0.7)
    json.dump(verdicts, open("tools/gh_verify_scan2_verdicts.json", "w"), indent=2)
    reals = [v for v in verdicts if v["verdict"] == "REAL"]
    print(f"\n=== REAL: {len(reals)} ===", flush=True)
    for v in reals:
        print(f"  {v['label']:10} {v['repo']:45} {v['path']:30} {v.get('secret')}", flush=True)
    print(f"\nsalvo tools/gh_verify_scan2_verdicts.json", flush=True)

if __name__ == "__main__":
    main()

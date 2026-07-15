#!/usr/bin/env python3
"""Focused refine on suspicious REAL candidates. Mask ALL secret material. Never print cleartext."""
import json, re, requests

RAW = "https://raw.githubusercontent.com/{repo}/{branch}/{path}"
SUSPECT = [
    ("diego3g/umbriel", ".env.local.example", "main", "AWS"),
    ("csrsm/go-proxy", "pk.txt", "main", "PEMkey"),
    ("limseang/film_api_new", "key.txt", "main", "PEMkey"),
    ("gauthieralfa/ep2510", "Priv.txt", "main", "PEMkey"),
    ("arcVaishali/stellar-vision", "text.txt", "main", "PEMkey"),
]
PEM_BODY = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----\n.*?\n-----END", re.S)

def mask(text):
    # AWS access key id
    text = re.sub(r"AKIA[0-9A-Z]{16}", lambda m: "AKIA***[MASKED]", text)
    # AWS secret
    text = re.sub(r"AWS_SECRET_ACCESS_KEY=[^\s]+", "AWS_SECRET_ACCESS_KEY=***[MASKED]", text)
    text = re.sub(r"(?im)^AWS_SECRET_ACCESS_KEY\s*=\s*\S+", "AWS_SECRET_ACCESS_KEY=***[MASKED]", text)
    # generic secret-looking assignments
    text = re.sub(r"(?i)(SECRET|PASSWORD|TOKEN|API_KEY|APIKEY|KEY)\s*=\s*[\"']?[A-Za-z0-9_\-]{12,}[\"']?",
                  lambda m: m.group(0).split("=")[0].strip()+"=***[MASKED]", text)
    # PEM
    text = re.sub(r"-----BEGIN [A-Z ]*PRIVATE KEY-----\n.*?\n-----END [A-Z ]*PRIVATE KEY-----",
                  "-----BEGIN ... PRIVATE KEY----- [BODY MASKED] -----END ...", text, flags=re.S)
    # gh/sk/AIza/xoxb
    text = re.sub(r"ghp_[0-9A-Za-z]{20,}", "ghp_***[MASKED]", text)
    text = re.sub(r"sk-[A-Za-z0-9]{10,}", "sk-***[MASKED]", text)
    text = re.sub(r"AIza[0-9A-Za-z_\-]{10,}", "AIza***[MASKED]", text)
    text = re.sub(r"xoxb-[^\"\s]+", "xoxb-***[MASKED]", text)
    text = re.sub(r"sk_live_[^\"\s]+", "sk_live_***[MASKED]", text)
    return text

def fetch(repo, path, branch):
    for b in (branch, "main", "master"):
        r = requests.get(RAW.format(repo=repo, branch=b, path=path), timeout=30)
        if r.status_code == 200:
            return r.text, b
    return None, None

for repo, path, branch, label in SUSPECT:
    content, b = fetch(repo, path, branch)
    if content is None:
        print(f"\n### {repo}/{path} -> FETCH FAIL"); continue
    # decision heuristic
    if label == "PEMkey":
        m = PEM_BODY.search(content)
        bodylen = len(m.group(0)) if m else 0
        real_like = bodylen > 150
    else:
        real_like = True
    print(f"\n### {repo} / {path} [{label}] branch={b} -> {'REAL-LIKE' if real_like else 'DOC'}")
    # show a small masked window (first 400 chars)
    print(mask(content)[:400])

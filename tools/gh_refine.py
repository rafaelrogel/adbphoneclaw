#!/usr/bin/env python3
"""Refine REAL candidates: show masked context, judge doc-vs-real. Never prints full secret."""
import json, re, requests

RAW = "https://raw.githubusercontent.com/{repo}/{branch}/{path}"
verdicts = json.load(open("tools/gh_verify_verdicts.json"))
reals = [v for v in verdicts if v["verdict"] == "REAL"]

DOCWORD = re.compile(r"(example|sample|for example|illustration|this is a|documentation|"
                     r"tutorial|you can use|e\.g\.|placeholder|your |fake|dummy|replace|"
                     r"paste|here\b|note:|suppose|imagine|demo)", re.I)
PEM_BODY = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----\n(.*?)\n-----END", re.S)

def mask_secret(text):
    text = re.sub(r"AKIA[0-9A-Z]{16}", lambda m: m.group(0)[:6]+"***"+m.group(0)[-2:], text)
    text = re.sub(r"ghp_[0-9A-Za-z]{36}", lambda m: m.group(0)[:6]+"***", text)
    text = re.sub(r"sk-[A-Za-z0-9]{20,}", lambda m: m.group(0)[:5]+"***", text)
    text = re.sub(r"AIza[0-9A-Za-z_\-]{35}", lambda m: m.group(0)[:6]+"***", text)
    text = re.sub(r"xoxb-[^\"\s]+", lambda m: m.group(0)[:8]+"***", text)
    text = re.sub(r"sk_live_[^\"\s]+", lambda m: m.group(0)[:10]+"***", text)
    # mask PEM body
    text = re.sub(r"-----BEGIN [A-Z ]*PRIVATE KEY-----\n.*?\n-----END [A-Z ]*PRIVATE KEY-----",
                  "-----BEGIN ... PRIVATE KEY----- [BODY MASKED] -----END ...", text, flags=re.S)
    return text

def fetch(repo, path, branch):
    for b in (branch, "main", "master"):
        if not b: continue
        r = requests.get(RAW.format(repo=repo, branch=b, path=path), timeout=30)
        if r.status_code == 200:
            return r.text
    return None

for v in reals:
    repo, path, label = v["repo"], v["path"], v["label"]
    branch = v.get("branch", "main")
    content = fetch(repo, path, branch)
    if content is None:
        print(f"\n### {repo} / {path} [{label}] -> FETCH FAIL"); continue
    # find lines around match
    if label == "PEMkey":
        m = PEM_BODY.search(content)
        if m:
            body = m.group(1)
            real_like = len(body) > 200 and not DOCWORD.search(body[:500])
            ctx = "PEM body len=%d -> %s" % (len(body), "REAL-LIKE" if real_like else "DOC/EXAMPLE")
        else:
            ctx = "no PEM body"
    else:
        # find first line with pattern, show +/-3 lines
        lines = content.splitlines()
        idx = 0
        for i, l in enumerate(lines):
            if re.search(r"AKIA|ghp_|sk-|AIza|xoxb-|sk_live_", l):
                idx = i; break
        window = lines[max(0,idx-3):idx+4]
        ctx = "\n".join(window)
        real_like = not DOCWORD.search("\n".join(window))
    print(f"\n### {repo} / {path} [{label}] -> {'REAL-LIKE' if real_like else 'DOC/EXAMPLE'}")
    print(mask_secret(ctx)[:600])

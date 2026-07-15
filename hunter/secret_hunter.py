#!/usr/bin/env python3
"""
A1 Secret Hunter — bug bounty / responsible disclosure only.
REGRA: nunca imprime o secret completo. Sempre mascara. Nunca testa/usa a chave.
Uso:
  python3 secret_hunter.py demo
  python3 secret_hunter.py scan "texto ou arquivo"
  python3 secret_hunter.py twitter "QUERY" --bearer SEU_TOKEN
"""
import re, sys, os, json

# Padrões de secret (regex) -> tipo + contato de disclosure
PATTERNS = {
    "AWS Access Key":   (r"AKIA[0-9A-Z]{16}", "aws-security@amazon.com / https://aws.amazon.com/security/vulnerability-reporting/"),
    "OpenAI API Key":   (r"sk-[A-Za-z0-9]{20,}", "security@openai.com"),
    "Slack Token":      (r"xox[baprs]-[0-9A-Za-z-]{10,}", "https://api.slack.com/security/disclosure"),
    "GitHub PAT":       (r"ghp_[A-Za-z0-9]{36,}", "GitHub Security Advisories / security@github.com"),
    "Stripe Live Key":  (r"sk_live_[A-Za-z0-9]{16,}", "security@stripe.com"),
    "Google API Key":   (r"AIza[0-9A-Za-z_\-]{35}", "Google VRP (g.co/vrp)"),
    "Twitter Bearer":   (r"AAAA[A-Za-z0-9%]{20,}", "X HackerOne program"),
    "Private Key":      (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "Depende do dono do certificado"),
}

def mask(secret: str) -> str:
    s = secret.strip()
    if len(s) <= 8:
        return s[:2] + "****" + s[-2:]
    return s[:4] + "****" + s[-4:]

def scan_text(text: str):
    findings = []
    for name, (pat, contact) in PATTERNS.items():
        for m in re.finditer(pat, text):
            secret = m.group(0)
            # contexto curto ao redor (pra reportar, não o secret)
            start = max(0, m.start() - 40)
            ctx = text[start:m.start()].replace("\n", " ") + "«MATCH»" + text[m.end():m.end()+40].replace("\n", " ")
            findings.append({
                "type": name,
                "masked": mask(secret),
                "disclosure": contact,
                "context": ctx.strip(),
            })
    return findings

def report(findings, source="<texto>"):
    if not findings:
        return f"[HUNTER] Nenhum secret encontrado em: {source}"
    lines = [f"[HUNTER] {len(findings)} candidato(s) em: {source}", "=" * 60]
    for f in findings:
        lines.append(f"• TIPO: {f['type']}")
        lines.append(f"  MASKED: {f['masked']}")
        lines.append(f"  CONTEXTO: ...{f['context']}...")
        lines.append(f"  DISCLOSURE: {f['disclosure']}")
        lines.append(f"  AÇÃO: reportar ao owner. NUNCA usar/testar a chave.")
        lines.append("-" * 60)
    return "\n".join(lines)

def demo():
    sample = """
    Cara, criei a integração mas travei. Meu token da AWS é AKIAIOSFODNN7EXAMPLE e o
    OpenAI sk-abc123DEF456ghi789JKL012mno345PQR678stu901vwx234yz. O Slack xoxb-1234567890-abcdefghijklmnop.
    O GitHub ghp_1234567890abcdefghijklmnopqrstuvwxyz0123. Stripe sk_live_1A2b3C4d5E6f7G8h9I0j.
    """
    print(report(scan_text(sample), "DEMO (dados falsos)"))

def scan(arg):
    if os.path.isfile(arg):
        text = open(arg, encoding="utf-8", errors="ignore").read()
    else:
        text = arg
    print(report(scan_text(text), arg[:60]))

def hunt_twitter(query, bearer):
    import requests
    url = "https://api.twitter.com/2/tweets/search/recent"
    params = {"query": query, "max_results": 100, "tweet.fields": "author_id,created_at"}
    headers = {"Authorization": f"Bearer {bearer}"}
    r = requests.get(url, params=params, headers=headers, timeout=20)
    if r.status_code != 200:
        print(f"[HUNTER] Erro Twitter API: {r.status_code} {r.text[:200]}")
        return
    data = r.json().get("data", [])
    print(f"[HUNTER] {len(data)} tweets retornados para: {query}")
    for t in data:
        f = scan_text(t.get("text", ""))
        if f:
            print(report(f, f"tweet {t.get('id')} por {t.get('author_id')}"))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "demo":
        demo()
    elif cmd == "scan":
        scan(sys.argv[2] if len(sys.argv) > 2 else "")
    elif cmd == "twitter":
        bearer = ""
        if "--bearer" in sys.argv:
            bearer = sys.argv[sys.argv.index("--bearer")+1]
        hunt_twitter(sys.argv[2] if len(sys.argv) > 2 else "", bearer)
    else:
        print(__doc__)

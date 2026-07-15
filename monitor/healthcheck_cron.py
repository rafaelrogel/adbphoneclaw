#!/usr/bin/env python3
"""Health check nginx + docker -> envia resultado pro WhatsApp do Rafael via CLI openclaw.
Near-zero token: subprocess puro + openclaw message send (sem LLM).
Cron: 0 */2 * * *  (todo 2h)
"""
import subprocess, sys, re, os, datetime, shutil

TARGET = "+351910070509"
NGINX_SITES_DIR = "/etc/nginx/sites-enabled"


def _openclaw():
    p = shutil.which("openclaw")
    if p:
        return p
    # fallback nvm
    cand = "/home/rafael/.nvm/versions/node/v24.16.0/bin/openclaw"
    return cand if os.path.exists(cand) else "openclaw"


def nginx_sites():
    names = set()
    try:
        for fn in os.listdir(NGINX_SITES_DIR):
            if fn.startswith("."):
                continue
            try:
                raw = open(os.path.join(NGINX_SITES_DIR, fn)).read()
            except Exception:
                continue
            txt = re.sub(r"#.*", "", raw)
            for m in re.finditer(r"server_name\s+([^;]+);", txt):
                for tok in m.group(1).split():
                    tok = tok.strip(";\"'")
                    if tok and tok != "_" and "." in tok:
                        names.add(tok)
    except Exception:
        pass
    filtered = [n for n in names
                if not (n.startswith("www.") and n[4:] in names)]
    return sorted(filtered)


def auth_protected_sites():
    names = set()
    try:
        for fn in os.listdir(NGINX_SITES_DIR):
            if fn.startswith("."):
                continue
            raw = open(os.path.join(NGINX_SITES_DIR, fn)).read()
            txt = re.sub(r"#.*", "", raw)
            if "auth_basic" not in txt:
                continue
            for m in re.finditer(r"server_name\s+([^;]+);", txt):
                for tok in m.group(1).split():
                    tok = tok.strip(";\"'")
                    if tok and tok != "_" and "." in tok:
                        names.add(tok)
    except Exception:
        pass
    return names


def check_sites():
    auth = auth_protected_sites()
    out = []
    for name in nginx_sites():
        code = "ERR"
        try:
            r = subprocess.run(
                ["curl", "-k", "-s", "-o", "/dev/null", "-m", "3", "-w",
                 "%{http_code}", "-H", f"Host: {name}", "https://127.0.0.1/"],
                capture_output=True, text=True, timeout=5)
            code = r.stdout.strip() or "000"
        except Exception:
            code = "ERR"
        out.append({"name": name, "code": code,
                    "ok": code.startswith(("2", "3")) or
                         (code == "401" and name in auth)})
    return out


def check_docker():
    out = []
    try:
        r = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}\t{{.Status}}"],
            capture_output=True, text=True, timeout=5)
        if r.returncode != 0:
            return [{"name": "docker", "status": "ERR", "ok": False}]
        for line in r.stdout.splitlines():
            if not line.strip():
                continue
            name, _, status = line.partition("\t")
            ok = status.startswith("Up") and "unhealthy" not in status.lower()
            out.append({"name": name.strip(), "status": status.strip(), "ok": ok})
    except FileNotFoundError:
        return [{"name": "docker", "status": "not installed", "ok": False}]
    except Exception:
        return [{"name": "docker", "status": "ERR", "ok": False}]
    return out


def fmt(sites, dockers):
    now = datetime.datetime.now().strftime("%H:%M")
    bad_sites = [s for s in sites if not s["ok"]]
    bad_dock = [d for d in dockers if not d["ok"]]
    if not bad_sites and not bad_dock:
        return (f"✅ Infra OK ({now})\n"
                f"🐳 docker: {sum(d['ok'] for d in dockers)}/{len(dockers)} up\n"
                f"🌐 sites nginx: {sum(s['ok'] for s in sites)}/{len(sites)} 2xx/3xx")
    lines = [f"⚠️ ALERTA infra ({now})"]
    if bad_dock:
        lines.append("🔴 docker down: " +
                     ", ".join(d["name"] for d in bad_dock))
    if bad_sites:
        lines.append("🔴 sites fora: " +
                     ", ".join(f"{s['name']}({s['code']})" for s in bad_sites))
    return "\n".join(lines)


def send(msg):
    env = dict(os.environ)
    env["PATH"] = "/home/rafael/.nvm/versions/node/v24.16.0/bin:" + env.get("PATH", "")
    subprocess.run([_openclaw(), "message", "send", "--channel", "whatsapp",
                    "--target", TARGET, "--message", msg], check=True, env=env)


if __name__ == "__main__":
    sites = check_sites()
    dockers = check_docker()
    msg = fmt(sites, dockers)
    try:
        send(msg)
        print(msg)
    except Exception as e:
        print("ERRO ao enviar:", e, file=sys.stderr)
        sys.exit(1)

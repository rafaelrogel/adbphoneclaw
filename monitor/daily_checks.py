#!/usr/bin/env python3
"""Daily briefing (cron 0 8 * * *): weather + disco/RAM/load + SSL expiry + domain expiry.
Envia resumo pro WhatsApp do Rafael via CLI openclaw (sem LLM -> near-zero token).
Reaproveita dominios do nginx (sites-enabled) pros checks SSL/domain.
"""
import subprocess, sys, re, os, datetime, shutil

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from healthcheck_cron import nginx_sites  # dominios locais

TARGET = "+351910070509"
LOCATION = "Lisbon"  # ajustar se precisar


def _openclaw():
    p = shutil.which("openclaw")
    if p:
        return p
    cand = "/home/rafael/.nvm/versions/node/v24.16.0/bin/openclaw"
    return cand if os.path.exists(cand) else "openclaw"


def weather():
    try:
        out = subprocess.run(["curl", "-s", "--max-time", "8",
                              f"wttr.in/{LOCATION}?format=3"],
                             capture_output=True, text=True, timeout=10).stdout.strip()
        return out or "clima n/a"
    except Exception:
        return "clima n/a"


def server_health():
    try:
        df = subprocess.run(["df", "-h", "/"], capture_output=True,
                            text=True).stdout.splitlines()[-1].split()
        disk_pct = df[4]
        disk_num = int(disk_pct.rstrip("%"))
    except Exception:
        disk_pct, disk_num = "?", 0
    try:
        ram = subprocess.run(["free", "-h"], capture_output=True,
                             text=True).stdout.splitlines()[1].split()
        ram_used, ram_total = ram[2], ram[1]
    except Exception:
        ram_used, ram_total = "?", "?"
    try:
        up = subprocess.run(["uptime"], capture_output=True,
                             text=True).stdout.strip()
        m = re.search(r"load average:\s*([0-9.,\s]+)", up)
        load = "load: " + m.group(1).strip() if m else up
    except Exception:
        load = "load n/a"
    return disk_pct, disk_num, ram_used, ram_total, load


def ssl_days(domain):
    try:
        cmd = (f"echo | openssl s_client -servername {domain} "
               f"-connect {domain}:443 2>/dev/null | openssl x509 -noout -enddate")
        out = subprocess.run(["bash", "-c", cmd], capture_output=True,
                             text=True, timeout=8).stdout
        m = re.search(r"notAfter=(.+)", out)
        if not m:
            return None
        s = m.group(1).strip()
        if s.endswith(" GMT"):
            s = s[:-4]
        exp = datetime.datetime.strptime(s, "%b %d %H:%M:%S %Y")
        return (exp - datetime.datetime.now()).days
    except Exception:
        return None


def whois_days(domain):
    try:
        out = subprocess.run(["whois", domain], capture_output=True,
                             text=True, timeout=12).stdout
    except FileNotFoundError:
        return "no_whois"
    except Exception:
        return None
    for line in out.splitlines():
        if re.search(r"Expiry Date|Expiration Date|Registrar Registration Expiration",
                     line, re.I):
            m = re.search(r"(\d{4}-\d{2}-\d{2})", line)
            if m:
                exp = datetime.datetime.strptime(m.group(1), "%Y-%m-%d")
                return (exp - datetime.datetime.now()).days
    return None


def fmt():
    now = datetime.datetime.now().strftime("%H:%M")
    lines = [f"🌅 Daily briefing ({now})"]
    # 4. weather
    lines.append(f"🌤 {weather()}")
    # 3. server health
    dp, dn, ru, rt, load = server_health()
    lines.append(f"💾 Disco: {dp} (/), RAM: {ru}/{rt}")
    lines.append(f"⚙️ {load}")
    if dn >= 85:
        lines[-2] += "  ⚠️ DISCO CHEIO"
    # 2 + 5. SSL + domain (por dominio do nginx)
    doms = nginx_sites()
    ssl_parts, dom_parts = [], []
    for d in doms:
        sd = ssl_days(d)
        if sd is None:
            ssl_parts.append(f"{d}=?")
        elif sd < 14:
            ssl_parts.append(f"{d}={sd}d ⚠️")
        else:
            ssl_parts.append(f"{d}={sd}d")
        wd = whois_days(d)
        if wd == "no_whois":
            dom_parts.append(f"{d}=whois?")
        elif wd is None:
            dom_parts.append(f"{d}=?")
        elif wd < 30:
            dom_parts.append(f"{d}={wd}d ⚠️")
        else:
            dom_parts.append(f"{d}={wd}d")
    lines.append("🔐 SSL: " + ", ".join(ssl_parts))
    lines.append("🌐 Domínios: " + ", ".join(dom_parts))
    return "\n".join(lines)


def send(msg):
    node_bin = "/home/rafael/.nvm/versions/node/v24.16.0/bin/node"
    env = dict(os.environ)
    env["PATH"] = "/home/rafael/.nvm/versions/node/v24.16.0/bin:" + env.get("PATH", "")
    subprocess.run([node_bin, _openclaw(), "message", "send", "--channel", "whatsapp",
                    "--target", TARGET, "--message", msg], check=True, env=env)


if __name__ == "__main__":
    msg = fmt()
    try:
        send(msg)
        print(msg)
    except Exception as e:
        print("ERRO ao enviar:", e, file=sys.stderr)
        sys.exit(1)

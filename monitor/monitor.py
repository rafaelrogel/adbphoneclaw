#!/usr/bin/env python3
"""A1 Live Monitor - backend (stdlib only). Serves the Habbo-style
status page and a JSON status endpoint. Designed to run behind nginx
basic auth at /monitor."""
import glob
import json
import mimetypes
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

BASE = os.path.dirname(os.path.abspath(__file__))
STATUS_FILE = os.path.join(BASE, "status.json")
CODER_STATUS_FILE = os.path.join(BASE, "status_coder.json")
INDEX_FILE = os.path.join(BASE, "index.html")
GW_PORT = 18789
ALLOWED_EXT = {".png", ".jpg", ".jpeg", ".gif", ".css", ".js", ".svg", ".webp"}
_last_cpu = {"total": 0, "idle": 0}


def cpu_percent():
    global _last_cpu
    try:
        parts = open("/proc/stat").readline().split()
        vals = [int(x) for x in parts[1:]]
        idle = vals[3]
        total = sum(vals)
        dtotal = total - _last_cpu["total"]
        didle = idle - _last_cpu["idle"]
        _last_cpu = {"total": total, "idle": idle}
        if dtotal <= 0:
            return 0.0
        return round((1 - didle / dtotal) * 100, 1)
    except Exception:
        return None


def system_stats():
    st = {}
    # CPU temp
    temp = None
    try:
        out = subprocess.run(["sensors", "-u"], capture_output=True, text=True, timeout=5).stdout
        temps = []
        for line in out.splitlines():
            m = re.match(r"\s*temp\d*_input:\s*([\d.]+)", line)
            if m:
                temps.append(float(m.group(1)))
        if temps:
            temp = max(temps)
    except Exception:
        pass
    if temp is None:
        mx = None
        for z in glob.glob("/sys/class/thermal/thermal_zone*/temp"):
            try:
                v = int(open(z).read().strip()) / 1000.0
                if mx is None or v > mx:
                    mx = v
            except Exception:
                pass
        temp = mx
    st["temp_c"] = round(temp, 1) if temp is not None else None
    st["cpu_pct"] = cpu_percent()
    # RAM
    try:
        mem = open("/proc/meminfo").read()
        def mi(k):
            m = re.search(r"^%s:\s+(\d+)\s*kB" % k, mem, re.M)
            return int(m.group(1)) * 1024 if m else None
        total = mi("MemTotal")
        avail = mi("MemAvailable")
        if total:
            used = total - (avail or 0)
            st["ram_total_gb"] = round(total / 1e9, 1)
            st["ram_used_gb"] = round(used / 1e9, 1)
            st["ram_pct"] = round(used / total * 100, 1)
    except Exception:
        pass
    # Disk
    try:
        du = shutil.disk_usage("/")
        st["disk_total_gb"] = round(du.total / 1e9, 1)
        st["disk_used_gb"] = round(du.used / 1e9, 1)
        st["disk_pct"] = round(du.used / du.total * 100, 1)
    except Exception:
        pass
    # Load
    try:
        l1, l5, l15 = open("/proc/loadavg").read().split()[:3]
        nproc = os.cpu_count() or 1
        st["load1"] = float(l1)
        st["load_pct"] = round(float(l1) / nproc * 100, 1)
        st["nproc"] = nproc
    except Exception:
        pass
    # Uptime
    try:
        up = float(open("/proc/uptime").read().split()[0])
        st["uptime_h"] = round(up / 3600, 1)
    except Exception:
        pass
    # SSL / domain expiry (cached)
    try:
        sv = ssl_info()
        st["ssl_min_days"] = min(sv.values()) if sv else None
    except Exception:
        pass
    try:
        dv = domain_info()
        st["domain_min_days"] = min(dv.values()) if dv else None
    except Exception:
        pass
    return st


# --- SSL / domain expiry (cached, heavy) ---
_SSL_CACHE = {"ts": 0, "data": {}}
_DOMAIN_CACHE = {"ts": 0, "data": {}}
_WHOIS_FMTS = [
    "%b %d %H:%M:%S %Y %Z", "%Y-%m-%dT%H:%M:%SZ",
    "%d-%b-%Y", "%Y-%m-%d", "%Y/%m/%d",
]


def _parse_whois_date(s):
    s = s.strip().replace(" 00:00:00", "")
    for f in _WHOIS_FMTS:
        try:
            return datetime.strptime(s, f)
        except Exception:
            continue
    return None


def ssl_info():
    now = time.time()
    if now - _SSL_CACHE["ts"] < 21600:
        return _SSL_CACHE["data"]
    out = {}
    for name in _nginx_site_names():
        try:
            cmd = ("echo | openssl s_client -servername %s -connect %s:443 "
                   "2>/dev/null | openssl x509 -noout -enddate" % (name, name))
            r = subprocess.run(["bash", "-c", cmd], capture_output=True,
                              text=True, timeout=10)
            m = re.search(r"notAfter=(.+)", r.stdout)
            if m:
                exp = _parse_whois_date(m.group(1).strip())
                if exp:
                    out[name] = max(0, int((exp.timestamp() - now) / 86400))
        except Exception:
            pass
    _SSL_CACHE.update(ts=now, data=out)
    return out


def domain_info():
    now = time.time()
    if now - _DOMAIN_CACHE["ts"] < 21600:
        return _DOMAIN_CACHE["data"]
    out = {}
    for name in _nginx_site_names():
        try:
            r = subprocess.run(["whois", name], capture_output=True,
                              text=True, timeout=15)
            for line in r.stdout.splitlines():
                if re.search(r"expir|registrar registration expiration", line, re.I):
                    mm = re.search(r"(\d{4}[-/]\d{2}[-/]\d{2}|\d{2}[- ][A-Za-z]{3}[- ]\d{4}|\w+ \d+ \d{4})", line)
                    if mm:
                        exp = _parse_whois_date(mm.group(1))
                        if exp:
                            out[name] = max(0, int((exp.timestamp() - now) / 86400))
                            break
        except Exception:
            pass
    _DOMAIN_CACHE.update(ts=now, data=out)
    return out


def log_tail(name, lines=50):
    files = {
        "monitor": "/tmp/monitor_run.log",
        "healthcheck": os.path.join(BASE, "healthcheck_cron.log"),
        "daily": os.path.join(BASE, "daily_checks.log"),
    }
    path = files.get(name)
    if not path or not os.path.isfile(path):
        return None, "log indisponivel: " + str(name)
    try:
        with open(path, "rb") as fh:
            data = fh.read().decode("utf-8", "replace")
        tail = "\n".join(data.splitlines()[-lines:])
        return tail, None
    except Exception as e:
        return None, str(e)


def gateway_alive():
    try:
        with socket.create_connection(("127.0.0.1", GW_PORT), timeout=1):
            return True
    except OSError:
        return False


def boot_time():
    try:
        with open("/proc/uptime") as f:
            return time.time() - float(f.read().split()[0])
    except Exception:
        return None


_SITES_CACHE = {"ts": 0.0, "data": []}
_SITES_TTL = 15.0
_DOCKER_CACHE = {"ts": 0.0, "data": []}
_DOCKER_TTL = 15.0


def docker_status():
    now = time.time()
    if now - _DOCKER_CACHE["ts"] < _DOCKER_TTL:
        return _DOCKER_CACHE["data"]
    out = []
    try:
        r = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}\t{{.Status}}"],
            capture_output=True, text=True, timeout=5)
        if r.returncode != 0:
            out = [{"name": "docker", "status": "ERR", "ok": False}]
        else:
            for line in r.stdout.splitlines():
                if not line.strip():
                    continue
                name, _, status = line.partition("\t")
                ok = status.startswith("Up") and "unhealthy" not in status.lower()
                out.append({"name": name.strip(), "status": status.strip(), "ok": ok})
    except FileNotFoundError:
        out = [{"name": "docker", "status": "not installed", "ok": False}]
    except Exception:
        out = [{"name": "docker", "status": "ERR", "ok": False}]
    _DOCKER_CACHE["ts"] = now
    _DOCKER_CACHE["data"] = out
    return out


def _nginx_site_names():
    names = set()
    d = "/etc/nginx/sites-enabled"
    try:
        for fn in os.listdir(d):
            if fn.startswith("."):
                continue
            try:
                raw = open(os.path.join(d, fn)).read()
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


def sites_status():
    now = time.time()
    if now - _SITES_CACHE["ts"] < _SITES_TTL:
        return _SITES_CACHE["data"]
    out = []
    for name in _nginx_site_names():
        code = "ERR"
        try:
            r = subprocess.run(
                ["curl", "-k", "-s", "-o", "/dev/null", "-m", "3",
                 "-w", "%{http_code}", "-H", f"Host: {name}",
                 "https://127.0.0.1/"],
                capture_output=True, text=True, timeout=5)
            code = r.stdout.strip() or "000"
        except Exception:
            code = "ERR"
        out.append({"name": name, "code": code})
    _SITES_CACHE["ts"] = now
    _SITES_CACHE["data"] = out
    return out


def load_status():
    try:
        with open(STATUS_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def load_coder_status():
    try:
        with open(CODER_STATUS_FILE) as f:
            return json.load(f)
    except Exception:
        return {}

_crypto_cache = {"ts": 0, "data": None}

def crypto_quotes():
    """Live BTC + DOGE in USD and EUR via CoinGecko free API (no key)."""
    now = time.time()
    if _crypto_cache["data"] and (now - _crypto_cache["ts"]) < 45:
        return _crypto_cache["data"]
    try:
        url = ("https://api.coingecko.com/api/v3/simple/price"
               "?ids=bitcoin,dogecoin&vs_currencies=usd,eur")
        req = urllib.request.Request(url, headers={"User-Agent": "A1-monitor/1.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            j = json.loads(r.read().decode())
        out = {
            "btc": {"usd": j["bitcoin"].get("usd"), "eur": j["bitcoin"].get("eur")},
            "doge": {"usd": j["dogecoin"].get("usd"), "eur": j["dogecoin"].get("eur")},
            "updated": int(now),
        }
        _crypto_cache["ts"] = now
        _crypto_cache["data"] = out
        return out
    except Exception as e:
        return _crypto_cache["data"] or {"btc": None, "doge": None, "error": str(e)}


def build_status():
    s = load_status()
    now = time.time()
    alive = gateway_alive()
    last_up = s.get("last_update", now)
    base_state = s.get("state", "online" if alive else "offline")
    gap = now - last_up
    # Two-tier auto state (evita "sempre dormindo"):
    #  - offline: continua offline
    #  - idle explicito: continua dormindo
    #  - working: apos 2min sem update -> online (andando/acordado)
    #  - online: so dorme (idle) apos 15min sem update
    if base_state == "offline":
        effective_state = "offline"
    elif base_state == "idle":
        effective_state = "idle"
    elif base_state == "working":
        effective_state = "working" if gap <= 120 else "online"
    else:  # online ou desconhecido
        effective_state = "idle" if gap > 900 else "online"
    # current_task só faz sentido enquanto trabalhando; fora disso, status neutro
    # (evita task travado tipo "respondendo Rafael" no HUD AGORA)
    if effective_state == "working":
        current_task = s.get("current_task", "—")
    else:
        current_task = {"online": "disponível", "idle": "ocioso",
                        "offline": "offline"}.get(effective_state, "disponível")

    # Agrupa containers Docker por projeto (Postiz + temporal* = Postiz, etc.)
    # Luzinha vermelha se QUALQUER membro do grupo cair.
    docker_flat = docker_status()
    PROJECT_RULES = [
        ("Postiz", ["postiz", "temporal"]),
        ("Cortes", ["cortespoliticos", "portal-cortes"]),
        ("NordicClaws", ["nordicclaws"]),
    ]
    groups = {}
    for c in docker_flat:
        proj = None
        for gname, prefixes in PROJECT_RULES:
            if any(c["name"].startswith(p) for p in prefixes):
                proj = gname
                break
        if proj is None:
            proj = c["name"]
        groups.setdefault(proj, []).append(c)
    docker = []
    for proj, members in groups.items():
        docker.append({
            "project": proj,
            "ok": all(m["ok"] for m in members),
            "members": members,
        })

    # Coder agent (separado)
    cs = load_coder_status()
    cnow = time.time()
    cbase = cs.get("state", "idle")
    cup = cnow - cs.get("last_update", cnow)
    if cbase == "offline":
        c_eff = "offline"
    elif cbase == "idle":
        c_eff = "idle"
    elif cbase == "working":
        c_eff = "working" if cup <= 120 else "online"
    else:
        c_eff = "idle" if cup > 900 else "online"
    if c_eff == "working":
        c_task = cs.get("current_task", "—")
    else:
        c_task = {"online": "disponível", "idle": "ocioso",
                  "offline": "offline"}.get(c_eff, "disponível")
    coder = {
        "agent": cs.get("agent", "Coder"),
        "model": cs.get("model", "openrouter/tencent/hy3:free"),
        "state": c_eff,
        "raw_state": cbase,
        "current_task": c_task,
        "activity": cs.get("activity", []),
    }

    stats = system_stats()
    try:
        up = sum(1 for c in docker_flat if c.get("ok"))
        stats["containers_up"] = up
        stats["containers_total"] = len(docker_flat)
    except Exception:
        pass

    return {
        "agent": s.get("agent", "A1"),
        "coder": coder,
        "model": s.get("model", "openrouter/tencent/hy3:free"),
        "session": s.get("session", ""),
        "state": effective_state,
        "raw_state": base_state,
        "current_task": current_task,
        "gateway_alive": alive,
        "server_time": now,
        "boot_time": boot_time(),
        "activity": s.get("activity", []),
        "last_update": last_up,
        "sites": sites_status(),
        "docker": docker,
        "stats": stats,
        "crypto": crypto_quotes(),
    }


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body).encode()
        elif isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path, ctype):
        with open(path, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        p = urlparse(self.path).path
        if p.startswith("/monitor"):
            p = p[len("/monitor"):] or "/"
        if p in ("/", "/index.html"):
            try:
                self._send_file(INDEX_FILE, "text/html; charset=utf-8")
            except Exception as e:
                self._send(500, {"error": str(e)})
        elif p == "/api/status":
            try:
                self._send(200, build_status())
            except Exception:
                # nunca derruba o fetch do browser (evita "CONEXAO PERDIDA")
                self._send(200, {
                    "agent": "A1", "state": "unknown", "gateway_alive": gateway_alive(),
                    "coder": {"agent": "Coder", "state": "unknown", "current_task": "—"},
                })
        else:
            fpath = os.path.normpath(os.path.join(BASE, p.lstrip("/")))
            ext = os.path.splitext(fpath)[1].lower()
            if (fpath.startswith(BASE) and os.path.isfile(fpath)
                    and ext in ALLOWED_EXT):
                ctype = mimetypes.guess_type(fpath)[0] or "application/octet-stream"
                self._send_file(fpath, ctype)
            else:
                self._send(404, {"error": "not found"})

    def do_POST(self):
        p = urlparse(self.path).path
        if p.startswith("/monitor"):
            p = p[len("/monitor"):] or "/"
        if p != "/api/action":
            self._send(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0") or "0")
            raw = self.rfile.read(length) if length else b"{}"
            data = json.loads(raw or b"{}")
        except Exception:
            data = {}
        action = (data.get("action") or "").strip()
        ok, msg = do_action(action, data.get("payload", {}))
        self._send(200, {"ok": ok, "action": action, "message": msg})

    def log_message(self, *a):
        pass


def _atomic_write_status(path, mutate):
    try:
        try:
            s = json.load(open(path))
        except Exception:
            s = {}
        mutate(s)
        s["last_update"] = time.time()
        tmp = path + ".{}.tmp".format(os.getpid())
        with open(tmp, "w") as fh:
            json.dump(s, fh)
        os.replace(tmp, path)
        return True, "ok"
    except Exception as e:
        return False, str(e)


def do_action(action, payload):
    if action == "restart_gateway":
        try:
            r = subprocess.run(["openclaw", "gateway", "restart"],
                              capture_output=True, text=True, timeout=120)
            return r.returncode == 0, (r.stdout + r.stderr).strip()[-400:]
        except Exception as e:
            return False, str(e)
    if action == "healthcheck":
        try:
            subprocess.Popen(["python3", os.path.join(BASE, "healthcheck_cron.py")],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True, "healthcheck iniciado"
        except Exception as e:
            return False, str(e)
    if action == "clear_activity":
        ok1, m1 = _atomic_write_status(STATUS_FILE, lambda s: s.__setitem__("activity", []))
        ok2, m2 = _atomic_write_status(CODER_STATUS_FILE, lambda s: s.__setitem__("activity", []))
        return ok1 and ok2, (m1 + "/" + m2)
    if action in ("coder_idle", "coder_offline"):
        st = "idle" if action == "coder_idle" else "offline"
        ok, m = _atomic_write_status(CODER_STATUS_FILE, lambda s: s.__setitem__("state", st))
        return ok, (m + " -> " + st)
    if action == "restart_container":
        name = (payload or {}).get("name", "")
        if not re.match(r"^[A-Za-z0-9._-]{1,60}$", name or ""):
            return False, "nome de container invalido"
        known = {c["name"] for c in docker_status()}
        if name not in known:
            return False, "container desconhecido: " + str(name)
        try:
            r = subprocess.run(["docker", "restart", name],
                              capture_output=True, text=True, timeout=120)
            return r.returncode == 0, (r.stdout + r.stderr).strip()[-400:]
        except Exception as e:
            return False, str(e)
    if action in ("container_stop", "container_start"):
        name = (payload or {}).get("name", "")
        if not re.match(r"^[A-Za-z0-9._-]{1,60}$", name or ""):
            return False, "nome de container invalido"
        known = {c["name"] for c in docker_status()}
        if name not in known:
            return False, "container desconhecido: " + str(name)
        verb = "stop" if action == "container_stop" else "start"
        try:
            r = subprocess.run(["docker", verb, name],
                              capture_output=True, text=True, timeout=120)
            return r.returncode == 0, (r.stdout + r.stderr).strip()[-400:]
        except Exception as e:
            return False, str(e)
    if action == "nginx_reload":
        try:
            r = subprocess.run(["sudo", "-n", "/usr/sbin/nginx", "-s", "reload"],
                              capture_output=True, text=True, timeout=30)
            return r.returncode == 0, (r.stdout + r.stderr).strip()[-300:] or "reload ok"
        except Exception as e:
            return False, str(e)
    if action == "nginx_restart":
        try:
            r = subprocess.run(["sudo", "-n", "systemctl", "restart", "nginx"],
                              capture_output=True, text=True, timeout=60)
            if r.returncode != 0:
                r = subprocess.run(["sudo", "-n", "/usr/sbin/nginx", "-s", "reload"],
                                  capture_output=True, text=True, timeout=30)
            return r.returncode == 0, (r.stdout + r.stderr).strip()[-300:] or "restart ok"
        except Exception as e:
            return False, str(e)
    if action == "reboot":
        try:
            subprocess.Popen(["sudo", "-n", "reboot"])
            return True, "reboot agendado"
        except Exception as e:
            return False, str(e)
    if action == "restart_monitor":
        try:
            script = ("sleep 1; fuser -k 8002/tcp; sleep 1; cd %s; setsid %s %s "
                      ">/tmp/monitor_run.log 2>&1 &" % (BASE, sys.executable,
                      os.path.abspath(__file__)))
            subprocess.Popen(["bash", "-c", script])
            return True, "monitor reiniciando..."
        except Exception as e:
            return False, str(e)
    if action == "coder_task":
        prompt = (payload or {}).get("prompt", "").strip()
        if not prompt:
            return False, "prompt vazio"
        if len(prompt) > 2000:
            prompt = prompt[:2000]
        try:
            r = subprocess.run(["openclaw", "agent", "--agent", "coder",
                              "-m", prompt, "--json"],
                              capture_output=True, text=True, timeout=300)
            out = (r.stdout + r.stderr).strip()[-500:]
            return r.returncode == 0, out or "coder executou"
        except Exception as e:
            return False, str(e)
    if action == "backup":
        try:
            ts = time.strftime("%Y%m%d-%H%M%S")
            dest = "/tmp/workspace_backup_%s.tar.gz" % ts
            r = subprocess.run(["tar", "czf", dest,
                              "--exclude=workspace/node_modules",
                              "--exclude=workspace/.git",
                              "--exclude=workspace/output",
                              "--exclude=workspace/output_prev*",
                              "--exclude=workspace/venv_producer",
                              "--exclude=*.png", "--exclude=*.jpg",
                              "--exclude=*.webp", "--exclude=*.mp4",
                              "--exclude=*.mp3", "--exclude=*.wav",
                              "--exclude=__pycache__",
                              "-C", "/home/rafael/.openclaw", "workspace"],
                              capture_output=True, text=True, timeout=180)
            if r.returncode != 0:
                return False, (r.stdout + r.stderr).strip()[-300:]
            sz = os.path.getsize(dest) / 1e6
            return True, "backup: %s (%.1f MB)" % (dest, sz)
        except Exception as e:
            return False, str(e)
    if action == "speed_test":
        try:
            r = subprocess.run(["bash", "-c",
              "curl -o /dev/null -s -w '%{time_total}' --max-time 10 https://1.1.1.1"],
              capture_output=True, text=True, timeout=15)
            t = r.stdout.strip()
            return True, "latencia externa: %s s" % t
        except Exception as e:
            return False, str(e)
    if action in ("systemd_start", "systemd_stop"):
        svc = (payload or {}).get("name", "")
        safe = ["nginx"]
        if svc not in safe:
            return False, "servico nao permitido: " + str(svc)
        verb = "start" if action == "systemd_start" else "stop"
        try:
            r = subprocess.run(["sudo", "-n", "systemctl", verb, svc],
                              capture_output=True, text=True, timeout=60)
            return r.returncode == 0, (r.stdout + r.stderr).strip()[-300:] or (verb + " ok")
        except Exception as e:
            return False, str(e)
    if action == "logs":
        name = (payload or {}).get("name", "monitor")
        lines = int((payload or {}).get("lines", 50))
        tail, err = log_tail(name, lines)
        if err:
            return False, err
        return True, tail or "(vazio)"

    return False, "acao desconhecida: " + str(action)


if __name__ == "__main__":
    port = int(os.environ.get("MONITOR_PORT", 8002))
    srv = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"A1 monitor listening on :{port}")
    srv.serve_forever()

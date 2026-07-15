#!/usr/bin/env python3
"""When 40 valid songs exist, deliver them via WhatsApp in batches of 10 (one audio msg each).
Runs in background, polls until ready, sends, tracks sent files. Idempotent.
"""
import subprocess, os, time, json

ROOT = "/home/rafael/.openclaw/workspace"
OUT = os.path.join(ROOT, "output")
OPENCLAW = "/home/rafael/.nvm/versions/node/v24.16.0/bin/openclaw"
TARGET = "+351910070509"
STATE = os.path.join(OUT, "delivered.json")
TOTAL = 40
BATCH = 10
POLL = 60
MAXWAIT = 6 * 3600  # 6h

def valid_mp3(path):
    if not os.path.exists(path):
        return False
    if os.path.getsize(path) < 100_000:
        return False
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration", "-of",
                        "default=noprint_wrappers=1:nokey=1", path],
                       capture_output=True, text=True)
    try:
        d = float(r.stdout.strip())
        return 270 <= d <= 300
    except Exception:
        return False

def load_sent():
    if os.path.exists(STATE):
        try:
            return set(json.load(open(STATE)).get("sent", []))
        except Exception:
            return set()
    return set()

def save_sent(s):
    json.dump({"sent": sorted(s)}, open(STATE, "w"))

def send_one(path):
    subprocess.run([OPENCLAW, "message", "send",
                    "--channel", "whatsapp", "--target", TARGET,
                    "--media", path],
                   capture_output=True, text=True, timeout=120)

def main():
    sent = load_sent()
    waited = 0
    while True:
        songs = [os.path.join(OUT, f"song_{i:02d}.mp3") for i in range(TOTAL)]
        valid = [p for p in songs if valid_mp3(p)]
        ready = len(valid)
        print(f"[deliver] valid={ready}/{TOTAL} sent={len(sent)}", flush=True)
        if ready >= TOTAL:
            break
        if waited >= MAXWAIT:
            print("[deliver] timeout waiting for songs", flush=True)
            return
        time.sleep(POLL)
        waited += POLL
    # deliver in batches of 10
    todo = [p for p in songs if valid_mp3(p) and os.path.basename(p) not in sent]
    print(f"[deliver] delivering {len(todo)} songs", flush=True)
    for idx, p in enumerate(todo):
        base = os.path.basename(p)
        try:
            send_one(p)
            sent.add(base)
            save_sent(sent)
            print(f"[deliver] sent {base} ({idx+1}/{len(todo)})", flush=True)
        except Exception as e:
            print(f"[deliver] FAILED {base}: {e}", flush=True)
        # pace: small gap between messages, bigger gap between batches
        if (idx + 1) % BATCH == 0:
            print(f"[deliver] batch done, pausing...", flush=True)
            time.sleep(15)
        else:
            time.sleep(3)
    print("[deliver] ALL SENT.", flush=True)

if __name__ == "__main__":
    main()

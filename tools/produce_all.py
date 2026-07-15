#!/usr/bin/env python3
"""Orchestrate 40 songs. Each song in its own subprocess (crash-isolated). Retry per song.
Resume: skips song_NN.mp3 that already exist with valid ~300s duration.
Usage: python3 produce_all.py [start] [count]
"""
import subprocess, os, sys, time

ROOT = "/home/rafael/.openclaw/workspace"
OUT = os.path.join(ROOT, "output")
TOTAL = 40
TIMEOUT = 600  # per song, seconds
RETRIES = 3

def valid_mp3(path):
    if not os.path.exists(path):
        return False
    if os.path.getsize(path) < 100_000:  # 100KB min
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

def main():
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    count = int(sys.argv[2]) if len(sys.argv) > 2 else (TOTAL - start)
    end = min(start + count, TOTAL)
    done = 0
    for i in range(start, end):
        out_path = os.path.join(OUT, f"song_{i:02d}.mp3")
        if valid_mp3(out_path):
            print(f"[{i:02d}/40] SKIP (valid exists)", flush=True)
            done += 1
            continue
        # cleanup any partial
        if os.path.exists(out_path):
            try: os.remove(out_path)
            except Exception: pass
        ok = False
        for attempt in range(1, RETRIES + 1):
            print(f"[{i:02d}/40] START attempt {attempt}", flush=True)
            try:
                rc = subprocess.run(
                    ["python3", "tools/produce_one.py", str(i)],
                    cwd=ROOT,
                    env={**os.environ, "PYTHONPATH": ROOT},
                    timeout=TIMEOUT,
                ).returncode
            except subprocess.TimeoutExpired:
                print(f"[{i:02d}/40] TIMEOUT after {TIMEOUT}s", flush=True)
                rc = 99
            except Exception as e:
                print(f"[{i:02d}/40] SPAWN ERROR: {e}", flush=True)
                rc = 98
            if rc == 0 and valid_mp3(out_path):
                ok = True
                break
            print(f"[{i:02d}/40] attempt {attempt} failed rc={rc}; retry", flush=True)
            time.sleep(5)
        if ok:
            done += 1
            print(f"[{i:02d}/40] OK ({done} done so far)", flush=True)
        else:
            print(f"[{i:02d}/40] GAVE UP after {RETRIES} attempts", flush=True)
        time.sleep(2)
    print(f"=== DONE. {done}/{TOTAL} valid. ===", flush=True)

if __name__ == "__main__":
    main()

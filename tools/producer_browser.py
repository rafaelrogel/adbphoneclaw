#!/usr/bin/env python3
"""Generate 40 ambient tracks from prompts.json, loop each to 5:00, save MP3. Resumable + auto-retry.

For each prompt:
  1. Fresh headless browser session (persistent login via storage_state).
  2. Generate (Sound description) on Flow Music.
  3. Poll /__api/clips for the new clip; wait for duration.status=completed.
  4. Download wav_url (public GCS bucket, no auth).
  5. Loop seamlessly to exactly 300s with ffmpeg, encode MP3 192k.
  6. Verify duration in 4:30-5:00. Save to output/song_NN.mp3.

Run: PYTHONPATH=/home/rafael/.openclaw/workspace python3 tools/producer_browser.py
Resume: re-run; existing song_NN.mp3 are skipped.
Retry: after first pass, retries any missing clip until all 40 done (or max passes).
"""
import tools.producer_common as C, json, re, subprocess, os, time, traceback

ROOT = "/home/rafael/.openclaw/workspace"
OUT = os.path.join(ROOT, "output")
os.makedirs(OUT, exist_ok=True)
PROMPTS = json.load(open(os.path.join(ROOT, "tools", "prompts.json")))
TARGET = 300  # seconds (5:00)
COOLDOWN = 5  # seconds between clips (reduce rate-limiting)
MAX_PASSES = 12  # total retry passes (incl first)

def ensure_loopable(prompt):
    p = prompt.strip()
    if not re.search(r"seamless loop", p, re.I):
        p = p.rstrip(". ") + ". Seamless loop."
    return p

def ffprobe_dur(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration", "-of",
                        "default=noprint_wrappers=1:nokey=1", path],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except Exception:
        return -1

def make_mp3(s, wav_url, out_path):
    data = s.page.context.request.get(wav_url).body()
    wav_tmp = out_path + ".tmp.wav"
    with open(wav_tmp, "wb") as f:
        f.write(data)
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                    "-stream_loop", "-1", "-i", wav_tmp, "-t", str(TARGET),
                    "-c:a", "libmp3lame", "-b:a", "192k", out_path], check=True)
    os.remove(wav_tmp)
    return ffprobe_dur(out_path)

def out_for(i):
    return os.path.join(OUT, f"song_{i:02d}.mp3")

def is_done(i):
    p = out_for(i)
    return os.path.exists(p) and p in done

manifest = os.path.join(OUT, "manifest.json")
done = {}
if os.path.exists(manifest):
    try:
        done = json.load(open(manifest))
    except Exception:
        done = {}

def gen_one(i):
    out_path = out_for(i)
    if is_done(i):
        print(f"[{i+1}/40] SKIP (exists)")
        return True
    prompt = ensure_loopable(PROMPTS[i])
    print(f"\n[{i+1}/40] PROMPT: {prompt[:70]}...")
    s = None
    try:
        s = C.ProducerSession()
        s.page.goto("https://www.flowmusic.app/session?t=true", timeout=60000)
        s.page.wait_for_timeout(3000)
        before = set(c["id"] for c in s.list_clips())
        s.page.evaluate("""(() => { const btns=[...document.querySelectorAll('button')];
          const b=btns.find(x=>{const l=(x.getAttribute('aria-label')||'').toLowerCase();
          return l.includes('sound')&&l.includes('expand');}); if(b)b.click(); })""")
        s.page.wait_for_timeout(800)
        s.page.evaluate("""(val) => { const el=document.querySelector("textarea[aria-label='Sound description']");
          const setter=Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype,'value').set;
          setter.call(el,val); el.dispatchEvent(new Event('input',{bubbles:true})); }""", prompt)
        s.page.wait_for_timeout(600)
        s.page.evaluate("""(() => { const g=[...document.querySelectorAll('button,[role=button]')]
          .find(x=>(x.innerText||'').includes('Generate')); if(g)g.click(); })""")
        new = None
        for k in range(72):  # up to 12 min
            time.sleep(10)
            try:
                cur = s.list_clips()
            except Exception:
                continue
            ids = [c["id"] for c in cur if c["id"] not in before]
            if ids:
                new = next(c for c in cur if c["id"] == ids[0])
                d = new.get("duration", {})
                if k % 3 == 0 or d.get("status") == "completed":
                    print(f"  [{k*10}s] clip {new['id'][:8]} status={d.get('status')} val={d.get('value')}")
                if d.get("status") == "completed":
                    break
            elif k % 6 == 0:
                print(f"  [{k*10}s] generating...")
        if not new:
            print(f"  [{i+1}/40] FAILED: no clip.")
            return False
        wav = new.get("wav_url") or new.get("audio_url")
        dur = make_mp3(s, wav, out_path)
        ok = 270 <= dur <= 300
        print(f"  [{i+1}/40] SAVED {out_path} dur={dur:.1f}s OK={ok}")
        done[out_path] = {"clip": new["id"], "prompt": prompt, "dur": dur, "ok": ok}
        json.dump(done, open(manifest, "w"), indent=1)
        return True
    except Exception as e:
        print(f"  [{i+1}/40] ERROR: {e}")
        traceback.print_exc()
        if os.path.exists(out_path):
            try: os.remove(out_path)
            except Exception: pass
        return False
    finally:
        if s:
            try: s.close()
            except Exception: pass

# ---- run ----
for attempt in range(MAX_PASSES):
    missing = [i for i in range(len(PROMPTS)) if not is_done(i)]
    if not missing:
        break
    print(f"\n=== PASS {attempt+1}/{MAX_PASSES}: {len(missing)} to do ===")
    for i in missing:
        gen_one(i)
        time.sleep(COOLDOWN)
    if attempt == 0:
        # already did first full pass; subsequent passes are retries only
        pass

remaining = [i for i in range(len(PROMPTS)) if not is_done(i)]
print(f"\n=== DONE. Manifest: {manifest} | missing: {remaining} ===")

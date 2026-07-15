#!/usr/bin/env python3
"""Produce exactly ONE song (index from argv). Isolated process: crash here kills only this song.
Usage: python3 produce_one.py <index>
Exit 0 on success, nonzero on failure.
"""
import tools.producer_common as C, json, re, subprocess, os, sys, time

ROOT = "/home/rafael/.openclaw/workspace"
OUT = os.path.join(ROOT, "output")
os.makedirs(OUT, exist_ok=True)
PROMPTS = json.load(open(os.path.join(ROOT, "tools", "prompts.json")))
TARGET = 300  # 5:00

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

def main():
    i = int(sys.argv[1])
    out_path = os.path.join(OUT, f"song_{i:02d}.mp3")
    prompt = ensure_loopable(PROMPTS[i])
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
                if d.get("status") == "completed":
                    break
            elif k % 6 == 0:
                print(f"  [{k*10}s] generating...", flush=True)
        if not new:
            print(f"[song {i:02d}] FAILED: no clip", flush=True)
            return 2
        wav = new.get("wav_url") or new.get("audio_url")
        dur = make_mp3(s, wav, out_path)
        ok = 270 <= dur <= 300
        print(f"[song {i:02d}] SAVED dur={dur:.1f}s OK={ok}", flush=True)
        if not ok:
            return 3
        return 0
    except Exception as e:
        print(f"[song {i:02d}] ERROR: {e}", flush=True)
        import traceback; traceback.print_exc()
        return 1
    finally:
        if s:
            try: s.close()
            except Exception: pass

if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""End-to-end test: strong 5-min prompt -> detect new clip -> download wav -> ffprobe."""
import tools.producer_common as C, json, re, subprocess, os, time

OUT = "/home/rafael/.openclaw/workspace/output"
os.makedirs(OUT, exist_ok=True)

STRONG = ("Instrumental ambient music. Exactly 5 minutes long (300 seconds, 5:00). "
          "Seamless continuous loop, no vocals, no drums, no percussion. "
          "Soft warm pads, gentle slow evolution, calm deep atmosphere, "
          "long sustained textures, very slow progression.")

s = C.ProducerSession()
before = set(c["id"] for c in s.list_clips())
print("clips before:", len(before))

# --- compose: expand Sound, set prompt, click Generate ---
s.page.evaluate("""(() => { const btns=[...document.querySelectorAll('button')];
  const b=btns.find(x=>{const l=(x.getAttribute('aria-label')||'').toLowerCase();
  return l.includes('sound')&&l.includes('expand');}); if(b)b.click(); })""")
s.page.wait_for_timeout(1000)
s.page.evaluate("""(val) => { const el=document.querySelector("textarea[aria-label='Sound description']");
  const setter=Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype,'value').set;
  setter.call(el,val); el.dispatchEvent(new Event('input',{bubbles:true})); }""", STRONG)
s.page.wait_for_timeout(800)
s.page.evaluate("""(() => { const g=[...document.querySelectorAll('button,[role=button]')]
  .find(x=>(x.innerText||'').includes('Generate')); if(g)g.click(); })""")
print("Generate clicked. Polling...")

new = None
for i in range(90):  # up to 15 min
    time.sleep(10)
    try:
        cur = s.list_clips()
    except Exception:
        continue
    ids = [c["id"] for c in cur if c["id"] not in before]
    if ids:
        new = next(c for c in cur if c["id"] == ids[0])
        d = new.get("duration", {})
        print(f"[{i*10}s] NEW {new['id']} status={d.get('status')} value={d.get('value')}")
        if d.get("status") == "completed":
            break
    elif i % 3 == 0:
        print(f"[{i*10}s] waiting...")

if not new:
    print("NO CLIP CREATED")
    s.close()
    raise SystemExit

wav = new.get("wav_url") or new.get("audio_url")
print("WAV URL:", wav)
# download (public bucket, no auth)
r = s.page.context.request.get(wav)
data = r.body()
path = os.path.join(OUT, new["id"] + ".wav")
with open(path, "wb") as f:
    f.write(data)
print("saved", path, len(data), "bytes")
dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                      "-of", "default=noprint_wrappers=1:nokey=1", path],
                     capture_output=True, text=True)
print("FFPROBE DURATION (s):", dur.stdout.strip())
s.close()

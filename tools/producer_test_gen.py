#!/usr/bin/env python3
"""TESTE v4: geracao robusta, espera 10min, deteccao ampla de export, baixa, verifica."""
import subprocess, time, os, json
from playwright.sync_api import sync_playwright

XVFB_DISPLAY = ":99"
if os.system(f"xdpyinfo -display {XVFB_DISPLAY} >/dev/null 2>&1") != 0:
    subprocess.Popen(["Xvfb", XVFB_DISPLAY, "-screen", "0", "1440x900x24", "-ac"],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
os.environ["DISPLAY"] = XVFB_DISPLAY

STORAGE = "/home/rafael/.openclaw/secrets/producer_storage_state.json"
OUT = "/home/rafael/.openclaw/workspace/output"
os.makedirs(OUT, exist_ok=True)
prompts = json.load(open("/home/rafael/.openclaw/workspace/tools/prompts.json"))
prompt = prompts[0]
print("PROMPT[0]:", prompt[:80])

with sync_playwright() as p:
    b = p.chromium.launch(headless=False,
                          args=["--disable-blink-features=AutomationControlled",
                                "--no-first-run", "--no-default-browser-check"])
    ctx = b.new_context(viewport={"width": 1440, "height": 900},
                        user_agent=("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                                    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.37"),
                        storage_state=STORAGE, accept_downloads=True)
    pg = ctx.new_page()
    pg.goto("https://www.flowmusic.app/session?t=true", timeout=30000)
    pg.wait_for_timeout(5000)

    pg.evaluate("""(() => {
        const btns=[...document.querySelectorAll('button')];
        const b=btns.find(x=>{const l=(x.getAttribute('aria-label')||'').toLowerCase(); return l.includes('sound') && l.includes('expand');});
        if(b) b.click();
    })()""")
    pg.wait_for_timeout(1500)
    pg.evaluate("""(val) => {
        const el = document.querySelector("textarea[aria-label='Sound description']");
        if(!el) return;
        const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
        setter.call(el, val);
        el.dispatchEvent(new Event('input', {bubbles:true}));
        el.dispatchEvent(new Event('change', {bubbles:true}));
    }""", prompt)
    pg.wait_for_timeout(1500)
    pg.evaluate("""(() => {
        const btns=[...document.querySelectorAll('button,[role=button]')];
        const g=btns.find(x=>(x.innerText||'').includes('Generate'));
        if(g) g.click();
    })()""")
    print("Generate clicado.")

    def find_export():
        # retorna info de possivel export
        return pg.evaluate("""(() => {
            const res={texts:[], aria:[], links:[], audios:0, hasplayer:false};
            document.querySelectorAll('button,a,[role=button]').forEach(e=>{
                const t=(e.innerText||'').trim();
                const al=(e.getAttribute('aria-label')||'').trim();
                const low=(t+' '+al).toLowerCase();
                if(t) res.texts.push(t.slice(0,40));
                if(al) res.aria.push(al.slice(0,50));
                if(/export|download|mp3|save|baixar|\\.wav|\\.mp3|more|\\.\\.\\./.test(low)) res.hit=low.slice(0,60);
            });
            document.querySelectorAll('a[download]').forEach(a=>res.links.push(a.getAttribute('download')||a.href));
            res.audios=document.querySelectorAll('audio').length;
            res.hasplayer = !!document.querySelector('audio, [aria-label*="player" i], [data-testid*="player"]');
            return res;
        })()""")

    export_clicked = False
    for i in range(120):  # 10 min
        time.sleep(5)
        info = find_export()
        hit = info.get('hit') if isinstance(info, dict) else None
        if hit:
            print(f"[{i*5}s] HIT export:", hit)
            # clica o elemento com hit
            try:
                with pg.expect_download(timeout=60000) as dl_info:
                    pg.evaluate("""(() => {
                        const els=[...document.querySelectorAll('button,a,[role=button]')];
                        const e=els.find(x=>{const low=((x.innerText||'')+' '+(x.getAttribute('aria-label')||'')).toLowerCase(); return /export|download|mp3|save|baixar/.test(low);});
                        if(e) e.click();
                    })()""")
                dl = dl_info.value
                path = os.path.join(OUT, dl.suggested_filename or "test1.mp3")
                dl.save_as(path)
                print("DOWNLOAD:", path)
                r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                    "-of", "default=noprint_wrappers=1:nokey=1", path],
                                   capture_output=True, text=True)
                print("DURACAO (s):", r.stdout.strip())
                export_clicked = True
                b.close()
                raise SystemExit
            except SystemExit:
                raise
            except Exception as e:
                print("erro download no hit:", e)
        if i % 12 == 0:
            print(f"[{i*5}s] gerando... audios={info.get('audios')} player={info.get('hasplayer')}")

    if not export_clicked:
        print("NAO achou export em 10min. Debug aria labels:")
        info = find_export()
        print("ARIA:", info.get('aria', [])[:30])
        print("TEXTS:", info.get('texts', [])[:30])
        pg.screenshot(path=f"{OUT}/test_no_export.png")
        b.close()

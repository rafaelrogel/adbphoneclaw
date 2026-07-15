#!/usr/bin/env python3
"""After Google One grant, click Remix and inspect dialog for extend/duration controls."""
import tools.producer_common as C, json, time

s = C.ProducerSession()
clips = s.list_clips(limit=10)
CLIP = clips[0]["id"]
conv = clips[0]["operation"].get("conversation_id")
s.page.goto("https://www.flowmusic.app/session/" + conv, timeout=60000)
s.page.wait_for_timeout(5000)

def dump(tag):
    info = s.page.evaluate("""() => { const out={texts:[],buttons:[]};
      document.querySelectorAll('button,[role=button],input,select,[role=option],textarea').forEach(e=>{
        const t=(e.innerText||'').trim().replace(/\\s+/g,' '); const al=e.getAttribute('aria-label')||'';
        const ph=e.getAttribute('placeholder')||'';
        if(t&&t.length<60)out.texts.push(t.slice(0,60)); if(al)out.buttons.push(al.slice(0,60));
        if(ph)out.buttons.push('ph:'+ph.slice(0,40)); });
      out.body=document.body.innerText.replace(/\\n+/g,' | ').slice(0,700); return out; }""")
    print(f"--- {tag} ---")
    print("TEXTS:", info['texts'][:50])
    print("BUTTONS/INPUTS:", info['buttons'][:50])
    print("BODY:", info['body'][:600])

print("BEFORE REMIX:")
dump("before")
s.page.evaluate("""() => { const e=[...document.querySelectorAll('button,[role=button]')]
  .find(x=>(x.getAttribute('aria-label')||'').includes('Remix')); if(e)e.click(); }""")
s.page.wait_for_timeout(3000)
print("AFTER REMIX:")
dump("after-remix")

# if a duration/length selector, try to set 5:00 / maximum
# inspect for sliders/selects/options mentioning minutes or length
info = s.page.evaluate("""() => {
  const found=[];
  document.querySelectorAll('input,select,[role=option],button,[role=radio]').forEach(e=>{
    const t=(e.innerText||'').trim(); const al=e.getAttribute('aria-label')||'';
    const ph=e.getAttribute('placeholder')||'';
    const low=(t+' '+al+' '+ph).toLowerCase();
    if(/min|length|duration|second|extend|longer|5:00|loop/.test(low)) found.push({t:t.slice(0,40),al:al.slice(0,40),ph:ph.slice(0,40),tag:e.tagName});
  });
  return found;
}""")
print("DURATION-RELATED CONTROLS:", json.dumps(info, indent=1)[:1500])
s.close()

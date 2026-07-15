#!/usr/bin/env python3
import tools.producer_common as C, json, time

s = C.ProducerSession()
CLIP = "d50a3447-d464-4e26-8a94-900a2d708743"
clips = s.list_clips(limit=30)
conv = next((c['operation'].get('conversation_id') for c in clips if c['id'] == CLIP), None)
s.page.goto("https://www.flowmusic.app/session/" + conv, timeout=60000)
s.page.wait_for_timeout(5000)

s.page.evaluate("""() => { const e=[...document.querySelectorAll('button,[role=button]')]
  .find(x=>(x.getAttribute('aria-label')||'').includes('Remix')); if(e)e.click(); }""")
s.page.wait_for_timeout(2500)

# click Dismiss by aria-label
s.page.evaluate("""() => { const els=[...document.querySelectorAll('button,[role=button]')];
  const d=els.find(x=>(x.getAttribute('aria-label')||'').trim()==='Dismiss'); if(d){d.click(); return 'dismissed';} return 'no-dismiss'; }""")
s.page.wait_for_timeout(2500)

info = s.page.evaluate("""() => {
   const out={texts:[],buttons:[]};
   document.querySelectorAll('button,[role=button],input,select,[role=option]').forEach(e=>{
      const t=(e.innerText||'').trim().replace(/\\s+/g,' ');
      const al=e.getAttribute('aria-label')||'';
      if(t && t.length<60) out.texts.push(t.slice(0,60));
      if(al) out.buttons.push(al.slice(0,60));
   });
   out.body=document.body.innerText.replace(/\\n+/g,' | ').slice(0,600);
   return out;
}""")
print("TEXTS:", info['texts'][:40])
print("BUTTONS:", info['buttons'][:40])
print("BODY:", info['body'][:500])
s.close()

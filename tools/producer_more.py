#!/usr/bin/env python3
import tools.producer_common as C, json, time

s = C.ProducerSession()
CLIP = "d50a3447-d464-4e26-8a94-900a2d708743"
clips = s.list_clips(limit=30)
conv = next((c['operation'].get('conversation_id') for c in clips if c['id'] == CLIP), None)
s.page.goto("https://www.flowmusic.app/session/" + conv, timeout=60000)
s.page.wait_for_timeout(5000)

# click More options (ellipsis)
s.page.evaluate("""() => { const e=[...document.querySelectorAll('button,[role=button]')]
  .find(x=>(x.getAttribute('aria-label')||'').includes('More options')); if(e)e.click(); }""")
s.page.wait_for_timeout(2000)

info = s.page.evaluate("""() => {
   const out={texts:[],buttons:[]};
   // radix menu renders in a portal; search whole doc for menu items
   const menu=document.querySelector('[role=menu]') || [...document.querySelectorAll('[data-state=open]')].find(e=>e.innerText&&e.innerText.length<400);
   const scope=menu||document;
   scope.querySelectorAll('button,[role=button],[role=menuitem],a').forEach(e=>{
      const t=(e.innerText||'').trim().replace(/\\s+/g,' ');
      const al=e.getAttribute('aria-label')||'';
      if(t && t.length<60) out.texts.push(t.slice(0,60));
      if(al) out.buttons.push(al.slice(0,60));
   });
   out.body=(scope.innerText||'').replace(/\\n+/g,' | ').slice(0,500);
   return out;
}""")
print("TEXTS:", info['texts'][:40])
print("BUTTONS:", info['buttons'][:40])
print("BODY:", info['body'][:400])
s.close()

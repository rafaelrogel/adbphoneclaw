#!/usr/bin/env python3
"""
voice_agent.py — Agente de voz HFP via PipeWire nativo (sem oFono/ADB).
Fluxo: bluez_input -> Vosk STT (PT-BR) -> LLM (MiMo) -> sherpa-onnx TTS -> bluez_output.

Discagem: org.pipewire.Telephony (D-Bus session).
Audio: pw-record / pw-play (PipeWire nativo).

Uso:
  voice_agent.py <numero> [--prompt "..."]
  voice_agent.py hangup
"""

import sys, os, json, time, subprocess, threading, queue, signal
import urllib.request as urllib_request
from urllib.request import urlopen as urllib_urlopen

# ---------- Paths ----------
HOME = os.path.expanduser("~")
SHERPA_BIN = f"{HOME}/.openclaw/tools/sherpa-onnx-tts/runtime/bin/sherpa-onnx-offline-tts"
TTS_MODEL = f"{HOME}/.openclaw/tools/sherpa-onnx-tts/models/vits-piper-pt_BR-edresson-low"
VOSK_MODEL = f"{HOME}/.openclaw/models/vosk/vosk-model-small-pt-0.3"

# ---------- LLM (MiMo Token Plan) ----------
LLM_URL = "https://token-plan-ams.xiaomimimo.com/v1/chat/completions"
LLM_KEY = "tp-ekfpad6ltgfkc3d0l0moh2wmlhffhs59au3pqr7pi9tb9w64"
LLM_MODEL = "mimo-v2.5"

# ---------- Telephony D-Bus ----------
SVC = "org.pipewire.Telephony"
AG = "/org/pipewire/Telephony/ag1"
VCM = "org.ofono.VoiceCallManager"
AGI = "org.pipewire.Telephony.AudioGateway1"

DEFAULT_PROMPT = (
    "Você é A1, um assistente telefônico automático e educado que fala português do Brasil. "
    "Você está em uma ligação real. Seja direto, natural e curto. "
    "Apresente-se brevemente, pergunte como pode ajudar, ouça, e responda de forma útil. "
    "Não invente dados. Mantenha cada resposta em no máximo 3 frases. "
    "Fale como se estivesse conversando por telefone."
)

stop = threading.Event()
busy = threading.Event()  # True enquanto LLM+TTS+play roda (pausa STT)

def busctl(*args):
    return subprocess.run(["busctl", "--user", *args], capture_output=True, text=True)

def dial(number):
    r = busctl("call", SVC, AG, VCM, "Dial", "s", number)
    print(f"[dial] {number}: {r.stdout.strip() or r.stderr.strip()}")

def hangup():
    busctl("call", SVC, AG, AGI, "HangupAll")
    print("[hangup] encerrado")

def call_active():
    r = busctl("call", SVC, AG, VCM, "GetCalls")
    return '"State" s "active"' in r.stdout

def get_bluez_nodes():
    try:
        out = subprocess.run(["pw-dump"], capture_output=True, text=True).stdout
        d = json.loads(out)
        inp = outp = None
        for o in d:
            if o.get("type") == "PipeWire:Interface:Node":
                n = o["info"].get("props", {}).get("node.name", "")
                if n.startswith("bluez_input"): inp = o["id"]
                elif n.startswith("bluez_output"): outp = o["id"]
        return inp, outp
    except Exception as e:
        print("[nodes] err", e); return None, None

# ---------- LLM ----------
def llm_respond(history):
    body = json.dumps({"model": LLM_MODEL, "messages": history, "max_tokens": 200}).encode()
    req = urllib_request.Request(LLM_URL, data=body, headers={
        "Authorization": f"Bearer {LLM_KEY}", "Content-Type": "application/json"})
    try:
        r = urllib_urlopen(req, timeout=40)
        return json.loads(r.read())["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print("[llm] err", e); return "Desculpe, não entendi."

# ---------- TTS ----------
def tts(text, out_wav):
    subprocess.run([SHERPA_BIN,
        "--vits-model", f"{TTS_MODEL}/pt_BR-edresson-low.onnx",
        "--vits-tokens", f"{TTS_MODEL}/tokens.txt",
        "--vits-data-dir", f"{TTS_MODEL}/espeak-ng-data",
        "--output-filename", out_wav, text],
        capture_output=True, timeout=60)
    return out_wav

def play(node_id, wav):
    subprocess.run(["pw-play", "--target", str(node_id),
        "--format", "s16", "--rate", "16000", "--channels", "1", wav],
        capture_output=True, timeout=30)

# ---------- STT ----------
def stt_loop(node_id, q):
    p = subprocess.Popen(["pw-record", "--target", str(node_id),
        "--format", "s16", "--rate", "8000", "--channels", "1", "-"],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    from vosk import Model, KaldiRecognizer
    rec = KaldiRecognizer(Model(VOSK_MODEL), 8000)
    while not stop.is_set():
        data = p.stdout.read(4000)
        if not data:
            time.sleep(0.1); continue
        if busy.is_set():
            continue
        if rec.AcceptWaveform(data):
            res = json.loads(rec.Result())
            txt = res.get("text", "").strip()
            if txt:
                q.put(txt)
    p.terminate()

def main():
    if len(sys.argv) < 2:
        print("uso: voice_agent.py <numero> | hangup"); sys.exit(1)
    if sys.argv[1] == "hangup":
        hangup(); return
    number = sys.argv[1]
    prompt = DEFAULT_PROMPT
    if "--prompt" in sys.argv:
        prompt = sys.argv[sys.argv.index("--prompt")+1]

    dial(number)
    print("[wait] aguardando atendimento...")
    for _ in range(40):
        if call_active(): break
        time.sleep(0.5)
    else:
        print("[wait] timeout sem atendimento, desligando"); hangup(); return
    print("[call] ATIVA")

    # espera nos de audio aparecerem
    inp = outp = None
    for _ in range(20):
        inp, outp = get_bluez_nodes()
        if inp and outp: break
        time.sleep(0.3)
    if not inp or not outp:
        print("[err] nos bluez nao apareceram"); hangup(); return
    print(f"[audio] input={inp} output={outp}")

    q = queue.Queue()
    history = [{"role": "system", "content": prompt}]
    t = threading.Thread(target=stt_loop, args=(inp, q), daemon=True)
    t.start()

    # fala inicial de abertura
    busy.set()
    first = "Olá, aqui é o assistente virtual A1. Em que posso ajudar?"
    print(f"[A1] {first}")
    tts(first, "/tmp/va_open.wav"); play(outp, "/tmp/va_open.wav")
    history.append({"role": "assistant", "content": first})
    busy.clear()

    print("[loop] ouvindo...")
    while not stop.is_set():
        try:
            txt = q.get(timeout=1)
        except queue.Empty:
            continue
        print(f"[caller] {txt}")
        history.append({"role": "user", "content": txt})
        busy.set()
        resp = llm_respond(history)
        print(f"[A1] {resp}")
        tts(resp, "/tmp/va_resp.wav"); play(outp, "/tmp/va_resp.wav")
        history.append({"role": "assistant", "content": resp})
        # mantem historico curto
        if len(history) > 12:
            history = [history[0]] + history[-10:]
        busy.clear()

def sig_handler(sig, frame):
    print("\n[signal] encerrando"); stop.set(); hangup()

if __name__ == "__main__":
    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)
    main()

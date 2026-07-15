#!/usr/bin/env python3
"""HFP voice conversation loop: Rafael (celular) <-> A1 (PC).

Pipeline:
  bluez_source...handsfree_audio_gateway  ->  Vosk STT (PT-BR)
                                          ->  MiMo (brain)
                                          ->  sherpa TTS (PT-BR)
                                          ->  bluez_sink...handsfree_audio_gateway
Call is placed via oFono (dbus-send). Runs under the vosk venv python.
"""
import os
import sys
import time
import json
import subprocess
import threading

# ---- paths ----
VOSK_MODEL = "/home/rafael/.openclaw/models/vosk/vosk-model-small-pt-0.3"
SHERPA_BIN = "/home/rafael/.openclaw/tools/sherpa-onnx-tts/runtime/bin/sherpa-onnx-offline-tts"
SHERPA_MODEL = "/home/rafael/.openclaw/tools/sherpa-onnx-tts/models/vits-piper-pt_BR-edresson-low/pt_BR-edresson-low.onnx"
SHERPA_TOKENS = "/home/rafael/.openclaw/tools/sherpa-onnx-tts/models/vits-piper-pt_BR-edresson-low/tokens.txt"
SHERPA_DATA = "/home/rafael/.openclaw/tools/sherpa-onnx-tts/models/vits-piper-pt_BR-edresson-low/espeak-ng-data"
MIMO_URL = "https://api.xiaomimimo.com/v1/chat/completions"
MIMO_KEY = "sk-e9pkm1h0v73eups1phb83sfl1oxyvkktjcalx5mv0x1e5dih"
MIMO_MODEL = "mimo-v2.5-pro"
TMP_WAV = "/tmp/hfp_reply.wav"

# ---- device discovery ----
def get_hfp():
    src = subprocess.run(["pactl", "list", "sources", "short"],
                         capture_output=True, text=True).stdout
    snk = subprocess.run(["pactl", "list", "sinks", "short"],
                         capture_output=True, text=True).stdout
    s = next((l.split()[1] for l in src.splitlines()
              if "handsfree_audio_gateway" in l and "monitor" not in l), None)
    k = next((l.split()[1] for l in snk.splitlines()
              if "handsfree_audio_gateway" in l), None)
    return s, k

# ---- oFono dial ----
def ofono_dial(number="+351910070509"):
    out = subprocess.run([
        "dbus-send", "--system", "--print-reply",
        "--dest=org.ofono",
        "/hfp/org/bluez/hci0/dev_50_13_1D_F5_E6_FC",
        "org.ofono.VoiceCallManager.Dial",
        f"string:{number}", "string:\"\""
    ], capture_output=True, text=True)
    return out.returncode == 0

def ofono_hangup():
    subprocess.run([
        "dbus-send", "--system", "--print-reply",
        "--dest=org.ofono",
        "/hfp/org/bluez/hci0/dev_50_13_1D_F5_E6_FC",
        "org.ofono.VoiceCallManager.HangupAll"
    ], capture_output=True)

def call_active():
    out = subprocess.run([
        "dbus-send", "--system", "--print-reply",
        "--dest=org.ofono",
        "/hfp/org/bluez/hci0/dev_50_13_1D_F5_E6_FC",
        "org.ofono.VoiceCallManager.GetCalls"
    ], capture_output=True, text=True).stdout
    return "voicecall" in out

# ---- MiMo brain ----
def mimo_reply(text, history):
    history.append({"role": "user", "content": text})
    # keep last 10 turns
    msgs = [{"role": "system",
             "content": "Voce e A1, assistente pessoal direto e curto do Rafael. "
                        "Responda em portugues (BR), frases curtas, sem firula."}] \
           + history[-10:]
    r = subprocess.run([
        "curl", "-s", "-X", "POST", MIMO_URL,
        "-H", "Content-Type: application/json",
        "-H", f"Authorization: Bearer {MIMO_KEY}",
        "-d", json.dumps({"model": MIMO_MODEL, "messages": msgs,
                          "temperature": 0.7, "max_tokens": 200})
    ], capture_output=True, text=True)
    try:
        data = json.loads(r.stdout)
        reply = data["choices"][0]["message"]["content"].strip()
    except Exception:
        reply = "(sem resposta do MiMo)"
    history.append({"role": "assistant", "content": reply})
    return reply

# ---- sherpa TTS -> HFP sink ----
def speak(text, sink):
    subprocess.run([SHERPA_BIN,
                    f"--vits-model={SHERPA_MODEL}",
                    f"--vits-tokens={SHERPA_TOKENS}",
                    f"--vits-data-dir={SHERPA_DATA}",
                    f"--output-filename={TMP_WAV}",
                    "--text", text[:400]],
                   capture_output=True)
    subprocess.run(["pacat", "--device", sink, TMP_WAV],
                   capture_output=True)

# ---- main ----
def main():
    from vosk import Model, KaldiRecognizer
    import requests  # available in venv

    print("[loop] Iniciando HFP voice loop", flush=True)

    # optional outbound dial: pass number as argv[1]
    dial_target = sys.argv[1] if len(sys.argv) > 1 else None
    if dial_target and not call_active():
        print(f"[loop] Disca {dial_target} via oFono...", flush=True)
        ofono_dial(dial_target)

    # wait for HFP devices (call active: inbound answered or outbound connected)
    src = snk = None
    for _ in range(60):
        src, snk = get_hfp()
        if src and snk:
            break
        time.sleep(1)
    if not src or not snk:
        print("[loop] HFP devices nao apareceram (nenhum call ativo). Saindo.", flush=True)
        return
    print(f"[loop] HFP OK: src={src} sink={snk}", flush=True)

    model = Model(VOSK_MODEL)
    rec = KaldiRecognizer(model, 16000)
    rec.SetWords(False)

    history = []
    speaking = threading.Event()  # true while we TTS-play

    # parec -> vosk
    parec = subprocess.Popen([
        "parec", "--format=s16le", "--rate=16000", "--channels=1",
        "--device", src
    ], stdout=subprocess.PIPE)

    print("[loop] Ouvindo... (fale no celular)", flush=True)
    try:
        while True:
            data = parec.stdout.read(4000)
            if not data:
                time.sleep(0.1)
                continue
            if rec.AcceptWaveform(data):
                res = json.loads(rec.Result())
                text = res.get("text", "").strip()
                if text:
                    print(f"[Rafael] {text}", flush=True)
                    reply = mimo_reply(text, history)
                    print(f"[A1] {reply}", flush=True)
                    speak(reply, snk)
            # partial results ignored for now
    except KeyboardInterrupt:
        print("[loop] Interrompido", flush=True)
    finally:
        parec.terminate()
        try:
            ofono_hangup()
        except Exception:
            pass

if __name__ == "__main__":
    main()

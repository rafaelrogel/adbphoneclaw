import os
import sys
import time
import re
import json
import logging
import struct
import subprocess
import requests
from client_adb.config import (
    BLUETOOTH_INPUT_DEVICE_NAME,
    BLUETOOTH_OUTPUT_DEVICE_NAME,
    RECORDINGS_DIR,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL
)
from client_adb.mimo_client import MimoClient
from client_adb.audio_bridge import (
    list_audio_devices,
    find_device_index,
    play_audio,
    play_audio_stream,
    record_speech
)
from client_adb.adb_controller import AdbController

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PW_CALL_SH = os.path.join(SCRIPT_DIR, "pw_call.sh")

# Configuração do Logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("PhoneClaw.MainAdb")

# Inicializações
mimo = MimoClient()
adb = AdbController()

# Histórico da conversa por voz
voice_history = []

def dial_hfp_pw(phone_number: str):
    """
    Disca via PipeWire HFP nativo (pw_call.sh agent).
    Retorna (input_idx, output_idx, proc) ou (None, None, None) em falha.
    Em modo agente o .sh sobe soh loopback de monitor (interlocutor->speakers)
    e imprime 'AGENT_READY cap=<src> pbk=<sink>'. O TTS do agente vai para o
    bluez_output via play_audio_stream (feito no loop de voz).
    """
    clean = re.sub(r"[^0-9+]", "", phone_number)
    logger.info(f"Disando HFP PipeWire (agent) para {clean}...")
    proc = subprocess.Popen(
        ["bash", PW_CALL_SH, "agent", clean],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    cap = pbk = None
    for line in proc.stdout:
        line = line.strip()
        logger.info(f"[pw_call] {line}")
        if line.startswith("AGENT_READY"):
            for tok in line.split():
                if tok.startswith("cap="):
                    cap = tok.split("=", 1)[1]
                elif tok.startswith("pbk="):
                    pbk = tok.split("=", 1)[1]
            break
        if "AVISO" in line or "timeout" in line or "nao atendeu" in line or "encerrada" in line:
            proc.wait()
            return None, None, None
    proc.wait()
    if not (cap and pbk):
        return None, None, None
    input_idx = find_device_index(cap, is_input=True)
    output_idx = find_device_index(pbk, is_input=False)
    if input_idx is None or output_idx is None:
        logger.error(f"Dispositivos bluez nao resolvidos no sounddevice: cap={cap} pbk={pbk}")
        hangup_hfp_pw()
        return None, None, None
    logger.info(f"HFP pronto: input_idx={input_idx} output_idx={output_idx}")
    return input_idx, output_idx, None


def hangup_hfp_pw():
    """Desliga chamada HFP (pw_call.sh hangup)."""
    logger.info("Desligando chamada HFP (pw_call.sh hangup)...")
    subprocess.run(["bash", PW_CALL_SH, "hangup"], check=False)


def get_bluez_node_ids():
    """
    Retorna (input_id, output_id) dos nos SCO via pw-dump.
    PipeWire expoe os nos mesmo quando o card profile esta 'off' (pactl nao enxerga),
    entao usamos os node IDs diretos com pw-record/pw-play (ver tools/voice_agent.py).
    """
    try:
        out = subprocess.run(["pw-dump"], capture_output=True, text=True).stdout
        d = json.loads(out)
        inp = outp = None
        for o in d:
            if o.get("type") == "PipeWire:Interface:Node":
                n = o.get("info", {}).get("props", {}).get("node.name", "")
                if n.startswith("bluez_input"):
                    inp = o["id"]
                elif n.startswith("bluez_output"):
                    outp = o["id"]
        return inp, outp
    except Exception as e:
        logger.error(f"pw-dump falhou: {e}")
        return None, None


def pw_record_segment(node_id, out_path, max_seconds: int = 8):
    """Grava segmento do bluez_input via pw-record (s16/16k/mono) ate max_seconds."""
    cmd = ["pw-record", "--target", str(node_id), "--format", "s16",
           "--rate", "16000", "--channels", "1", "--max-time", str(max_seconds), out_path]
    try:
        subprocess.run(cmd, capture_output=True, timeout=max_seconds + 5)
    except Exception as e:
        logger.error(f"pw-record erro: {e}")
    if os.path.exists(out_path) and os.path.getsize(out_path) > 44:
        return out_path
    return None


def pw_play_wav(node_id, wav_path):
    """Reproduz wav no bluez_output via pw-play (formato lido do header)."""
    subprocess.run(["pw-play", "--target", str(node_id), wav_path],
                   capture_output=True, timeout=30)


def dial_hfp_pw(phone_number: str):
    """
    Disca via PipeWire HFP nativo (pw_call.sh).
    Retorna (input_node_id, output_node_id) dos nos SCO, ou (None, None).
    Usa pw-dump (node IDs) + pw-record/pw-play no loop de voz.
    """
    clean = re.sub(r"[^0-9+]", "", phone_number)
    logger.info(f"Disando HFP PipeWire para {clean}...")
    proc = subprocess.Popen(
        ["bash", PW_CALL_SH, clean],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    answered = False
    for line in proc.stdout:
        line = line.strip()
        logger.info(f"[pw_call] {line}")
        if line == "ANSWERED":
            answered = True
            break
        if "timeout" in line or "encerrada" in line:
            proc.wait()
            return None, None
    proc.wait()
    if not answered:
        return None, None
    in_id = out_id = None
    for _ in range(60):
        in_id, out_id = get_bluez_node_ids()
        if in_id and out_id:
            break
        time.sleep(0.5)
    if not (in_id and out_id):
        logger.error("Nos bluez (SCO) nao apareceram apos atender.")
        hangup_hfp_pw()
        return None, None
    logger.info(f"HFP pronto: bluez_input={in_id} bluez_output={out_id}")
    return in_id, out_id


def run_hfp_loop(input_id, output_id, contact, active_device_id):
    """
    Loop de voz HFP nativo: pw-record no bluez_input (ASR) e pw-play no
    bluez_output (TTS). Node IDs passados direto (pactl nao enxerga os nos).
    """
    logger.info("=== LOOP HFP (pw-record/pw-play) ===")
    saud = "Olá, aqui é A1, o assistente do Rafael. Em que posso ajudar?"
    _tts_play_hfp(saud, output_id)

    conversando = True
    while conversando:
        seg = pw_record_segment(input_id, "temp_input.wav", max_seconds=8)
        if not seg:
            logger.info("Sem audio (silencio/EOF). Aguardando...")
            continue
        transcription = mimo.transcribe_audio(seg)
        if os.path.exists("temp_input.wav"):
            os.remove("temp_input.wav")
        if not transcription:
            logger.info("Transcricao em branco. Tentando novamente...")
            continue
        print(f"\n[Interlocutor]: {transcription}")
        if "tchau" in transcription.lower() or "desligar" in transcription.lower():
            conversando = False
        response_text = generate_agent_response(transcription)
        print(f"[PhoneClaw Agent]: {response_text}\n")
        _tts_play_hfp(response_text, output_id)

    logger.info("Encerrando chamada HFP...")
    hangup_hfp_pw()


def _tts_play_hfp(text, output_id):
    """Sintetiza via MiMo e reproduz no bluez_output via pw-play."""
    path = "temp_tts.wav"
    if mimo.synthesize_speech(text, path):
        pw_play_wav(output_id, path)
    else:
        logger.error("Falha na sintese de voz (TTS).")


def make_wav_header(pcm_data_len: int, sample_rate: int = 16000, channels: int = 1, bits_per_sample: int = 16) -> bytes:
    """
    Gera um cabeçalho WAV de 44 bytes para dados PCM brutos.
    """
    byte_rate = sample_rate * channels * bits_per_sample // 8
    block_align = channels * bits_per_sample // 8
    
    header = struct.pack('<4sI4s4sIHHIIHH4sI',
        b'RIFF',
        pcm_data_len + 36,
        b'WAVE',
        b'fmt ',
        16,
        1,  # Formato PCM Linear
        channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b'data',
        pcm_data_len
    )
    return header

def call_ollama(messages: list, model: str = OLLAMA_MODEL, timeout: int = 60) -> str:
    """
    Chama o LLM local (Ollama) em http://localhost:11434/api/chat.
    Retorna o texto da resposta ou string vazia em caso de falha.
    """
    url = f"{OLLAMA_BASE_URL.rstrip('/')}/api/chat"
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
    }
    try:
        resp = requests.post(url, json=payload, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        return data.get("message", {}).get("content", "").strip()
    except Exception as e:
        logger.error(f"Erro ao chamar Ollama local ({url}): {e}")
        return ""

def generate_agent_response(user_text: str) -> str:
    """
    Cérebro da IA: texto transcrito -> LLM local (Ollama) -> resposta.
    Mantém histórico em voice_history para contexto de conversa.
    """
    global voice_history
    voice_history.append({"role": "user", "content": user_text})

    system_prompt = (
        "Você é A1, assistente pessoal do Rafael. "
        "Responda em português brasileiro, curto e direto."
    )
    messages = [{"role": "system", "content": system_prompt}] + voice_history

    response = call_ollama(messages)

    if not response:
        # Fallback caso o Ollama não esteja rodando.
        response = f"Identifiquei a frase: '{user_text}'. (LLM local indisponível)"

    voice_history.append({"role": "assistant", "content": response})
    return response

def run_voice_conversation_loop(input_idx: int, output_idx: int, contact: str, active_device_id: str, monitor_input: bool = True, use_hfp: bool = False):
    """
    Loop principal de conversação de voz na chamada telefônica.
    Grava os turnos e salva a ligação inteira localmente no Homelab.
    """
    # PhoneClaw: transcricao usa MONITOR do sink BT (voz que VEM da chamada),
    # nao mic local -> elimina eco acustico do fone pro mic.
    # Em modo HFP (use_hfp) o input ja eh o bluez_source (voz do interlocutor),
    # entao nao sobrescreve com monitor.
    if monitor_input and BLUETOOTH_OUTPUT_DEVICE_NAME:
        mon_name = BLUETOOTH_OUTPUT_DEVICE_NAME + ".monitor"
        mon_idx = find_device_index(mon_name, is_input=True)
        if mon_idx is not None:
            logger.info(f"Input transcricao -> monitor sink BT idx {mon_idx} (voz do interlocutor)")
            input_idx = mon_idx
    if use_hfp:
        run_hfp_loop(input_idx, output_idx, contact, active_device_id)
        return

    logger.info("==================================================")
    logger.info("INICIANDO CONVERSAÇÃO DE VOZ (CHAMADA ATIVA VIA USB)")
    logger.info("Fale próximo ao microfone do Bluetooth.")
    logger.info("Diga 'Tchau' ou 'Desligar' para encerrar.")
    logger.info("==================================================")
    
    call_start_time = time.time()
    pcm_segments = []
    
    # Saudação inicial do agente
    saudacao = "Olá, aqui é A1, o assistente do Rafael. Isto é um teste do PhoneClaw, tudo bem?"
    
    tts_chunks = []
    def stream_and_capture_initial(text):
        for chunk in mimo.synthesize_speech_stream(text, style="Happy"):
            tts_chunks.append(chunk)
            yield chunk
            
    play_audio_stream(stream_and_capture_initial(saudacao), output_idx)
    
    # Processa cabeçalho da saudação
    tts_full = b"".join(tts_chunks)
    if tts_full.startswith(b"RIFF") and len(tts_full) > 44:
        tts_full = tts_full[44:]
    if tts_full:
        pcm_segments.append(tts_full)
    
    conversando = True
    while conversando:
        # 1. Escuta o interlocutor via microfone Bluetooth (ASR)
        temp_input_path = "temp_input.wav"
        recorded_file = record_speech(input_idx, output_path=temp_input_path, silence_seconds=1.8, max_seconds=12.0)
        
        if not recorded_file:
            logger.info("Nenhum áudio capturado (silêncio). Aguardando...")
            continue
            
        # Armazena o áudio do interlocutor no buffer
        try:
            with open(recorded_file, "rb") as f:
                user_wav = f.read()
            if user_wav.startswith(b"RIFF") and len(user_wav) > 44:
                user_pcm = user_wav[44:]
                pcm_segments.append(user_pcm)
        except Exception as e:
            logger.error(f"Erro ao ler gravação de entrada: {e}")

        # 2. Transcreve com a API Xiaomi MiMo
        transcription = mimo.transcribe_audio(recorded_file)
        
        if os.path.exists(temp_input_path):
            os.remove(temp_input_path)
            
        if not transcription:
            logger.info("Transcrição em branco. Tentando novamente...")
            continue
            
        print(f"\n[Interlocutor]: {transcription}")
        
        # Verifica se o interlocutor encerrou
        if "tchau" in transcription.lower() or "desligar" in transcription.lower():
            conversando = False
            
        # 3. Gera resposta da IA
        response_text = generate_agent_response(transcription)
        print(f"[PhoneClaw Agent]: {response_text}\n")
        
        # 4. Sintetiza a resposta e reproduz na chamada
        tts_reply_chunks = []
        def stream_and_capture_reply(text):
            for chunk in mimo.synthesize_speech_stream(text, style="Happy"):
                tts_reply_chunks.append(chunk)
                yield chunk
                
        play_audio_stream(stream_and_capture_reply(response_text), output_idx)

        # Pausa pos-TTS: deixa sink esvaziar p/ nao gravar propria voz no prox turno (anti-eco)
        time.sleep(0.8)

        # Armazena o áudio do agente no buffer
        reply_full = b"".join(tts_reply_chunks)
        if reply_full.startswith(b"RIFF") and len(reply_full) > 44:
            reply_full = reply_full[44:]
        if reply_full:
            pcm_segments.append(reply_full)

    logger.info("Desligando chamada...")
    if use_hfp:
        hangup_hfp_pw()
    else:
        adb.end_call(active_device_id)
    
    # 5. Costura e grava a chamada finalizada no Homelab
    if pcm_segments:
        if not os.path.exists(RECORDINGS_DIR):
            os.makedirs(RECORDINGS_DIR)
            
        full_pcm = b"".join(pcm_segments)
        wav_header = make_wav_header(len(full_pcm))
        
        timestamp_ms = int(call_start_time * 1000)
        duration_seconds = int(time.time() - call_start_time)
        fileName = os.path.join(RECORDINGS_DIR, f"call_{contact}_{timestamp_ms}.wav")
        
        try:
            with open(fileName, "wb") as f:
                f.write(wav_header + full_pcm)
            logger.info(f"Gravação da chamada salva localmente com sucesso!")
            logger.info(f"Local: {fileName} | Duração: {duration_seconds} segundos")
        except Exception as e:
            logger.error(f"Erro ao salvar gravação da chamada: {e}")
    else:
        logger.warning("Nenhum áudio foi capturado para gravação.")

def setup_audio_devices():
    list_audio_devices()
    
    input_idx = find_device_index(BLUETOOTH_INPUT_DEVICE_NAME, is_input=True)
    output_idx = find_device_index(BLUETOOTH_OUTPUT_DEVICE_NAME, is_input=False)
    
    if input_idx is None:
        try:
            val = input("\nDigite o ID do dispositivo de entrada (Microfone Bluetooth HFP): ")
            input_idx = int(val)
        except ValueError:
            input_idx = None
            
    if output_idx is None:
        try:
            val = input("Digite o ID do dispositivo de saída (Alto-falante Bluetooth HFP): ")
            output_idx = int(val)
        except ValueError:
            output_idx = None
            
    return input_idx, output_idx

def main():
    logger.info("Iniciando PhoneClaw ADB-Only...")
    
    # 1. Verifica dispositivos USB
    devices = adb.get_connected_devices()
    if not devices:
        logger.error("Nenhum celular detectado via USB (ADB). Conecte o cabo e ative a Depuração USB.")
        sys.exit(1)
        
    logger.info(f"Dispositivos USB detectados: {devices}")
    active_device_id = devices[0]
    logger.info(f"Usando o dispositivo padrão: {active_device_id}")
    
    # 2. Configura áudio Bluetooth HFP
    input_idx, output_idx = setup_audio_devices()
    
    while True:
        print("\n=== MENU PHONECLAW USB/ADB ===")
        print("1. Disparar ligação celular (GSM) via ADB")
        print("2. Abrir chat do WhatsApp via ADB")
        print("3. Sair")
        
        opcao = input("Escolha uma opção: ").strip()
        
        if opcao == "1":
            num = input("Número para ligar (ex: +5511999999999): ").strip()
            if num:
                print("Disando via HFP PipeWire (pw_call.sh agent)...")
                in_idx, out_idx, _ = dial_hfp_pw(num)
                if in_idx is None or out_idx is None:
                    print("Falha HFP. Tentando fallback ACTION_CALL via ADB...")
                    if adb.make_gsm_call(num, active_device_id):
                        print("Aguardando 5 segundos para a chamada completar...")
                        time.sleep(5)
                        run_voice_conversation_loop(input_idx, output_idx, num, active_device_id)
                else:
                    run_voice_conversation_loop(in_idx, out_idx, num, active_device_id, monitor_input=False, use_hfp=True)
            else:
                print("Número inválido.")
                
        elif opcao == "2":
            num = input("Número para WhatsApp (ex: +5511999999999): ").strip()
            if num:
                if adb.make_whatsapp_call(num, active_device_id):
                    print("Por favor, ative a chamada de voz no WhatsApp do celular.")
                    print("Aguardando ativação da chamada (pressione Enter para iniciar o loop de voz)...")
                    input()
                    run_voice_conversation_loop(input_idx, output_idx, num, active_device_id)
            else:
                print("Número inválido.")
                
        elif opcao == "3":
            print("Encerrando PhoneClaw ADB-Only...")
            sys.exit(0)
        else:
            print("Opção inválida.")

if __name__ == "__main__":
    main()

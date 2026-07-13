import os
import sys
import time
import logging
import struct
from client_adb.config import (
    BLUETOOTH_INPUT_DEVICE_NAME,
    BLUETOOTH_OUTPUT_DEVICE_NAME,
    RECORDINGS_DIR
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

def generate_agent_response(user_text: str) -> str:
    """
    Simula o cérebro da IA (LLM).
    Pode ser integrado ao OpenClaw, Ollama ou APIs como Gemini/OpenAI.
    """
    global voice_history
    user_text_lower = user_text.lower()
    
    if "olá" in user_text_lower or "oi" in user_text_lower:
        response = "Olá! Aqui é o assistente virtual PhoneClaw, rodando em modo local via USB. Como posso te ajudar?"
    elif "como estás" in user_text_lower or "tudo bem" in user_text_lower:
        response = "Estou operacional no Homelab, controlando o telefone por comandos ADB."
    elif "tchau" in user_text_lower or "desligar" in user_text_lower or "adeus" in user_text_lower:
        response = "Entendido. Finalizando a chamada via USB. Até logo!"
    else:
        response = f"Identifiquei a frase: '{user_text}'. Sou um agente de voz local controlando este dispositivo."
        
    voice_history.append({"role": "user", "content": user_text})
    voice_history.append({"role": "assistant", "content": response})
    return response

def run_voice_conversation_loop(input_idx: int, output_idx: int, contact: str, active_device_id: str):
    """
    Loop principal de conversação de voz na chamada telefônica.
    Grava os turnos e salva a ligação inteira localmente no Homelab.
    """
    logger.info("==================================================")
    logger.info("INICIANDO CONVERSAÇÃO DE VOZ (CHAMADA ATIVA VIA USB)")
    logger.info("Fale próximo ao microfone do Bluetooth.")
    logger.info("Diga 'Tchau' ou 'Desligar' para encerrar.")
    logger.info("==================================================")
    
    call_start_time = time.time()
    pcm_segments = []
    
    # Saudação inicial do agente
    saudacao = "Alô! Conexão USB e áudio ativos. Como posso ajudar?"
    
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
        
        # Armazena o áudio do agente no buffer
        reply_full = b"".join(tts_reply_chunks)
        if reply_full.startswith(b"RIFF") and len(reply_full) > 44:
            reply_full = reply_full[44:]
        if reply_full:
            pcm_segments.append(reply_full)

    logger.info("Desligando chamada via ADB...")
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
                if adb.make_gsm_call(num, active_device_id):
                    print("Aguardando 5 segundos para a chamada completar...")
                    time.sleep(5)
                    run_voice_conversation_loop(input_idx, output_idx, num, active_device_id)
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

import os
import time
import queue
import logging
import sounddevice as sd
import soundfile as sf
import numpy as np
from client_adb.config import SAMPLE_RATE, CHANNELS, CHUNK_SIZE

logger = logging.getLogger("PhoneClaw.AudioBridge")

def list_audio_devices():
    """
    Lista todos os dispositivos de áudio disponíveis no sistema.
    """
    logger.info("Listando dispositivos de áudio disponíveis:")
    try:
        devices = sd.query_devices()
        for idx, dev in enumerate(devices):
            input_channels = dev.get('max_input_channels', 0)
            output_channels = dev.get('max_output_channels', 0)
            print(f"[{idx}] {dev['name']} - Canais Entrada: {input_channels}, Canais Saída: {output_channels} ({dev.get('hostapi')})")
    except Exception as e:
        logger.error(f"Erro ao listar dispositivos de áudio: {str(e)}")

def find_device_index(name_pattern: str, is_input: bool = True) -> int:
    """
    Encontra o índice do dispositivo de áudio que contenha o nome_pattern no nome.
    """
    if not name_pattern:
        return None
        
    try:
        devices = sd.query_devices()
        for idx, dev in enumerate(devices):
            max_ch = dev.get('max_input_channels', 0) if is_input else dev.get('max_output_channels', 0)
            if max_ch > 0 and name_pattern.lower() in dev['name'].lower():
                logger.info(f"Dispositivo selecionado: [{idx}] {dev['name']}")
                return idx
    except Exception as e:
        logger.error(f"Erro ao buscar dispositivo por nome '{name_pattern}': {str(e)}")
    return None

def play_audio(file_path: str, device_index: int = None):
    """
    Reproduz um arquivo de áudio WAV no alto-falante selecionado (ou padrão se None).
    """
    if not os.path.exists(file_path):
        logger.error(f"Arquivo de áudio não encontrado para reproduzir: {file_path}")
        return

    try:
        data, fs = sf.read(file_path)
        logger.info(f"Iniciando reprodução do áudio: {file_path} no dispositivo {device_index or 'padrão'}...")
        sd.play(data, fs, device=device_index)
        sd.wait()  # Aguarda a reprodução terminar
        logger.info("Reprodução concluída.")
    except Exception as e:
        logger.error(f"Erro durante a reprodução de áudio: {str(e)}")

def record_speech(device_index: int = None, output_path: str = "temp_input.wav", 
                  threshold: float = 0.015, silence_seconds: float = 1.5, max_seconds: float = 15.0) -> str:
    """
    Grava áudio do microfone selecionado até detectar silêncio.
    Retorna o caminho do arquivo WAV gerado ou string vazia se falhar.
    """
    q = queue.Queue()

    def callback(indata, frames, time, status):
        if status:
            logger.warning(f"Status do áudio: {status}")
        q.put(indata.copy())

    logger.info("Aguardando fala... Fale agora.")
    
    try:
        stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            device=device_index,
            callback=callback,
            blocksize=CHUNK_SIZE
        )
    except Exception as e:
        logger.error(f"Erro ao abrir canal de gravação: {str(e)}")
        return ""

    audio_frames = []
    has_spoken = False
    silence_start_time = None
    start_time = time.time()
    
    with stream:
        while True:
            try:
                data = q.get(timeout=0.1)
                audio_frames.append(data)
                
                rms = np.sqrt(np.mean(data ** 2))
                
                if rms > threshold:
                    if not has_spoken:
                        logger.info("Fala detectada...")
                        has_spoken = True
                    silence_start_time = None
                else:
                    if has_spoken:
                        if silence_start_time is None:
                            silence_start_time = time.time()
                        elif time.time() - silence_start_time >= silence_seconds:
                            logger.info("Silêncio detectado após fala. Parando gravação.")
                            break
                            
                if time.time() - start_time >= max_seconds:
                    logger.info("Tempo máximo de gravação atingido.")
                    break
            except queue.Empty:
                continue

    if not audio_frames:
        return ""

    audio_data = np.concatenate(audio_frames, axis=0)
    
    if not has_spoken:
        logger.info("Nenhuma fala detectada.")
        return ""

    try:
        sf.write(output_path, audio_data, SAMPLE_RATE)
        logger.info(f"Gravação salva com sucesso em: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Erro ao gravar arquivo de áudio: {str(e)}")
        return ""

def play_audio_stream(audio_generator, device_index: int = None):
    """
    Reproduz chunks de áudio recebidos de um gerador diretamente no alto-falante Bluetooth.
    """
    stream = None
    is_first_chunk = True
    
    try:
        for chunk in audio_generator:
            if not chunk:
                continue
                
            if is_first_chunk:
                if len(chunk) > 44:
                    chunk = chunk[44:]
                is_first_chunk = False
            
            if stream is None:
                stream = sd.RawOutputStream(
                    samplerate=SAMPLE_RATE,
                    channels=CHANNELS,
                    dtype='int16',
                    device=device_index
                )
                stream.start()
                logger.info("Iniciando reprodução em tempo real (streaming)...")
            
            stream.write(chunk)
            
    except Exception as e:
        logger.error(f"Erro ao reproduzir áudio em tempo real: {str(e)}")
    finally:
        if stream is not None:
            try:
                stream.stop()
                stream.close()
            except Exception:
                pass
            logger.info("Reprodução em tempo real concluída.")

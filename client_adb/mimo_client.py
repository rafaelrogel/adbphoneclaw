import base64
import requests
import json
import logging
from client_adb.config import XIAOMI_MIMO_API_KEY, XIAOMI_MIMO_BASE_URL

logger = logging.getLogger("PhoneClaw.MimoClient")

class MimoClient:
    def __init__(self):
        self.api_key = XIAOMI_MIMO_API_KEY
        self.base_url = XIAOMI_MIMO_BASE_URL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}"
        }

    def transcribe_audio(self, audio_file_path: str) -> str:
        """
        Envia um arquivo de áudio local para a API da Xiaomi MiMo ASR e retorna o texto.
        Endpoint: /chat/completions com content do tipo input_audio (OpenAI-compatible).
        """
        url = f"{self.base_url}/chat/completions"
        logger.info(f"Enviando áudio para transcrição (ASR)... Arquivo: {audio_file_path}")

        try:
            with open(audio_file_path, 'rb') as audio_file:
                audio_b64 = base64.b64encode(audio_file.read()).decode('utf-8')

            payload = {
                "model": "mimo-v2.5-asr",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_audio",
                                "input_audio": {
                                    "data": audio_b64,
                                    "format": "wav"
                                }
                            }
                        ]
                    }
                ]
            }

            headers = self.headers.copy()
            headers["Content-Type"] = "application/json"
            response = requests.post(url, headers=headers, json=payload)

            if response.status_code == 200:
                result = response.json()
                choices = result.get("choices", [])
                if choices:
                    transcription = choices[0].get("message", {}).get("content", "").strip()
                    logger.info(f"Transcrição bem-sucedida: '{transcription}'")
                    return transcription
                else:
                    logger.error("Nenhuma escolha de resposta retornada pela API ASR.")
                    return ""
            else:
                logger.error(f"Erro na transcrição Xiaomi ASR ({response.status_code}): {response.text}")
                return ""
        except Exception as e:
            logger.error(f"Falha de rede ou leitura ao transcrever: {str(e)}")
            return ""

    def synthesize_speech(self, text: str, output_file_path: str, voice: str = "mimo_default", style: str = None) -> bool:
        """
        Envia um texto para a API da Xiaomi MiMo TTS e salva o áudio de retorno.
        """
        url = f"{self.base_url}/chat/completions"
        logger.info(f"Enviando texto para síntese de voz (TTS)... Texto: '{text}'")

        content = text
        if style:
            content = f"<style>{style}</style>{text}"

        payload = {
            "model": "mimo-v2.5-tts",
            "messages": [
                {
                    "role": "assistant",
                    "content": content
                }
            ],
            "audio": {
                "format": "wav",
                "voice": voice
            }
        }

        try:
            headers = self.headers.copy()
            headers["Content-Type"] = "application/json"
            
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                try:
                    choices = result.get("choices", [])
                    if choices:
                        message = choices[0].get("message", {})
                        audio_data = message.get("audio", {})
                        base64_audio = audio_data.get("data", "")
                        
                        if base64_audio:
                            audio_bytes = base64.b64decode(base64_audio)
                            with open(output_file_path, 'wb') as out_file:
                                out_file.write(audio_bytes)
                            logger.info(f"Voz sintetizada salva com sucesso em: {output_file_path}")
                            return True
                        else:
                            logger.error("Dados de áudio não encontrados na resposta da API.")
                    else:
                        logger.error("Nenhuma escolha de resposta retornada pela API.")
                except Exception as ex:
                    logger.error(f"Erro ao extrair/decodificar áudio base64: {str(ex)}")
                
                return False
            else:
                logger.error(f"Erro na síntese Xiaomi TTS ({response.status_code}): {response.text}")
                return False
        except Exception as e:
            logger.error(f"Falha de rede ou escrita ao sintetizar voz: {str(e)}")
            return False

    def synthesize_speech_stream(self, text: str, voice: str = "mimo_default", style: str = None):
        """
        Envia um texto para a API da Xiaomi MiMo TTS e retorna um gerador de bytes de áudio decodificados (PCM).
        """
        url = f"{self.base_url}/chat/completions"
        logger.info(f"Iniciando síntese de voz em streaming (TTS)... Texto: '{text}'")

        content = text
        if style:
            content = f"<style>{style}</style>{text}"

        payload = {
            "model": "mimo-v2.5-tts",
            "messages": [
                {
                    "role": "assistant",
                    "content": content
                }
            ],
            "audio": {
                "format": "wav",
                "voice": voice
            },
            "stream": True
        }

        try:
            headers = self.headers.copy()
            headers["Content-Type"] = "application/json"
            
            response = requests.post(url, headers=headers, json=payload, stream=True)
            
            if response.status_code == 200:
                for line in response.iter_lines():
                    if line:
                        line_str = line.decode("utf-8").strip()
                        if line_str.startswith("data:"):
                            data_str = line_str[5:].strip()
                            if data_str == "[DONE]":
                                break
                            try:
                                chunk_json = json.loads(data_str)
                                choices = chunk_json.get("choices", [])
                                if choices:
                                    delta = choices[0].get("delta", {})
                                    audio_data = delta.get("audio", {})
                                    base64_audio = audio_data.get("data", "")
                                    if base64_audio:
                                        yield base64.b64decode(base64_audio)
                            except Exception:
                                continue
            else:
                logger.error(f"Erro no streaming Xiaomi TTS ({response.status_code}): {response.text}")
        except Exception as e:
            logger.error(f"Falha de rede no streaming: {str(e)}")

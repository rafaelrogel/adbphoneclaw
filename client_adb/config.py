import os

# CONFIGURAÇÕES DA API XIAOMI MIMO
# A chave é lida da variável de ambiente XIAOMI_MIMO_API_KEY.
# Defina no sistema antes de rodar (ex: export XIAOMI_MIMO_API_KEY="sua_chave").
XIAOMI_MIMO_API_KEY = os.environ.get("XIAOMI_MIMO_API_KEY", "SUA_API_KEY_AQUI")
XIAOMI_MIMO_BASE_URL = "https://api.xiaomimimo.com/v1"

# CONFIGURAÇÕES DE ÁUDIO BLUETOOTH
# O script listará os dispositivos no início se deixados em None.
BLUETOOTH_INPUT_DEVICE_NAME = None
BLUETOOTH_OUTPUT_DEVICE_NAME = None

# PARÂMETROS TÉCNICOS DE ÁUDIO
SAMPLE_RATE = 16000  # Frequência recomendada para ASR/TTS (16kHz)
CHANNELS = 1         # Canal mono para voz
CHUNK_SIZE = 1024    # Tamanho do bloco para captura

# DIRETÓRIO PARA GRAVAÇÕES DE CHAMADAS (No Homelab/PC)
RECORDINGS_DIR = "./call_records"

# CONFIGURAÇÃO DO LLM LOCAL (Ollama) usado por generate_agent_response()
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:1b")

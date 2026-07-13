# PhoneClaw ADB-Only Bridge (Sem APK)

Este repositório contém a versão do **PhoneClaw** que roda localmente no **Homelab**, controlando o celular Android conectado via USB (ADB) sem instalar nenhum APK. A ponte de áudio da chamada usa **Bluetooth HFP** pareado entre celular e computador.

## Estrutura do Repositório

```
adbphoneclaw/
├── client_adb/                 # Pacote Python do cliente
│   ├── __init__.py
│   ├── config.py               # Config real (lê env XIAOMI_MIMO_API_KEY, OLLAMA_*)
│   ├── adb_controller.py       # Comandos ADB: discar, desligar, WhatsApp
│   ├── mimo_client.py          # ASR/TTS da API Xiaomi MiMo
│   └── audio_bridge.py         # Captura/reprodução via Bluetooth (import lazy do sounddevice)
├── config.py.example           # Template de configuração
├── main_adb.py                 # Menu CLI interativo + loop de voz
├── openclaw_skill_adb.py       # Skills para importar no OpenClaw
├── test_phoneclaw_adb.py       # Testes (pytest)
├── conftest.py                 # Stub de áudio p/ rodar testes em ambiente headless
└── requirements.txt
```

## Pré-requisitos

1. **ADB** instalado e no PATH (`which adb`). Instale se faltar: `sudo apt-get install android-tools-adb`.
2. **Depuração USB** ativa no celular.
3. **Bluetooth HFP** pareado (PC como headset de voz).
4. **Ollama** local rodando em `http://localhost:11434` (LLM da resposta).
   - Modelo padrão: `llama3.2:1b` (já disponível). Troque via env `OLLAMA_MODEL`.

## Como Instalar e Rodar

```bash
pip install -r requirements.txt          # sounddevice, soundfile, numpy, requests, pytest
export XIAOMI_MIMO_API_KEY="sua_chave"   # necessário p/ ASR/TTS da MiMo
# OLLAMA_BASE_URL / OLLAMA_MODEL são opcionais (defaults locais)
python main_adb.py
```

`config.py` (dentro de `client_adb/`) já lê a chave MiMo da env `XIAOMI_MIMO_API_KEY`.
Se preferir, copie `config.py.example` como base de referência.

## LLM da resposta (generate_agent_response)

Integrado ao **Ollama local** (`http://localhost:11434/api/chat`):
texto transcrito → LLM → resposta em português. Mantém `voice_history` para contexto.
System prompt: *"Você é A1, assistente pessoal do Rafael. Responda em português brasileiro, curto e direto."*
Fallback: se o Ollama não responder, devolve uma mensagem de erro local (sem quebrar o loop).

## Testes

```bash
python -m pytest test_phoneclaw_adb.py -v
```

`conftest.py` injeta um stub de `sounddevice` quando não há backend de áudio
(ambiente headless/CI), permitindo coletar e rodar os testes sem hardware.

## Skills OpenClaw

`openclaw_skill_adb.py` expõe:
- `phoneclaw_adb_gsm_call(to)`
- `phoneclaw_adb_whatsapp_chat(to)`
- `phoneclaw_adb_end_call()`

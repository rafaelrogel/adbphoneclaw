# PLANO: Inference Box (OpenClaw + adbphoneclaw + celular com plano)

Box dedicada. Roda OpenClaw (agente) + adbphoneclaw (ponte ADB) + celular Android
com plano dados+voz. Vira operador de telefone autônomo: liga, manda WhatsApp,
transcreve, responde via LLM.

Baseado em lições reais do homelab (ver MEMORY.md). Não pular seção 9 (gotchas).

---

## 1. HARDWARE

- **Mini PC x86_64**: Intel N100 / Ryzen 5xxx / qualquer com USB3. 8GB RAM, 128GB SSD.
  - Se usar LLM local (Ollama llama3.2:1b): 8GB ok. Se MiMo/OpenRouter via API: 4GB ok.
  - Ethernet + WiFi.
- **Dongle BT OBRIGATÓRIO**: Realtek **RTL8761B** (lsusb `0bda:8771`).
  - Verificar no boot: `hciconfig -a hciX | grep "SCO MTU"` → **RX deve ser > 0**.
  - ❌ NÃO usar: CSR `0a12:0001` (SCO MTU RX=0, inútil), Qualcomm integrado
    (rejeita eSCO 0x0d), WiFi dongle `0bda:c811` (é WiFi, não cria hciX).
- **Celular Android** com plano dados+voz: moto g35 testado e funciona.
  - USB debugging ON, autorizar host (one-time).
  - Tela com PIN (script desbloqueia, ADB não desbloqueia sozinho).
- **Cabo USB** de dados (não só carga).

## 2. OS

- Ubuntu 24.04 LTS ou Debian 12. Kernel ≥ 5.8 (módulo `btrtl` suporta RTL8761B).
- Usuário com `sudo -n` NOPASSWD (pro adbphoneclaw rodar comandos sem senha).

## 3. INSTALAÇÃO BASE

```bash
sudo apt-get update
sudo apt-get install -y android-tools-adb bluez bluez-tools ofono \
  pipewire pipewire-pulse wireplumber libspa-0.2-bluetooth \
  git python3 python3-venv
# Ollama local (opcional, se não usar API):
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2:1b
```

## 4. BLUETOOTH / HFP (áudio da ligação — parte crítica)

HFP exige **backend oFono**, não WirePlumber native (native NÃO registra HFP).

1. **bt-agent.service** (auto-confirma pareamento, NoInputNoOutput):
   - script `/home/<user>/.openclaw/tools/bt_agent.py` (Agent1 NoInputNoOutput)
   - systemd `/etc/systemd/system/bt-agent.service` (root, Restart=always, enabled)
2. **WirePlumber conf** (`/usr/share/wireplumber/wireplumber.conf` ou
   `/home/<user>/.config/wireplumber/wireplumber.conf.d/51-bluez-cvsd.conf`):
   ```
   monitor.bluez.properties = {
     bluez5.hfphsp-backend = "ofono"
     bluez5.codecs = [ "cvsd" ]
     bluez5.hw-offload-sco = false
   }
   ```
3. **Patch oFono CVSD** (força CVSD, evita crash mSBC):
   - `tools/patch_ofono_cvsd.sh` (patcheia `ofono_handsfree_audio_has_wideband` → return 0)
   - **Reaplicar após `apt upgrade` do ofono.**
4. **Parear celular**: tipo BT = "Fones de ouvido" + toggle "Chamadas" ON.
5. **Teste SCO**: `tools/hfp_sco_test.sh` ou `tools/hfp_accept_sco.sh` →
   `Synchronous Connect Complete` deve retornar **0x00** e nós
   `bluez_input`/`bluez_output` aparecem em `pactl`.

## 5. ADB / CELULAR

```bash
adb devices          # celular deve aparecer com "device" (autorizado)
```
- **Desbloquear tela** (ADB não faz sozinho):
  ```bash
  adb shell input keyevent 224        # wake
  adb shell input text 416669         # PIN (trocar pelo real)
  adb shell input keyevent 66         # ENTER
  ```
- **adbphoneclaw** (já em `~/Vibecoding/adbphoneclaw`):
  - `make_gsm_call` → disca chip via ACTION_CALL (funciona).
  - `make_whatsapp_call` → **SÓ ABRE tela** (não disca VoIP) → precisa `input tap`
    no botão de call ou toque manual.
  - `run_voice_conversation_loop` → escuta **mic local do PC** (BT source),
    **NÃO transcreve interlocutor remoto** (limitação conhecida).
  - `client_adb/config.py` → lê `XIAOMI_MIMO_API_KEY` (ASR/TTS MiMo), `OLLAMA_*`.

## 6. adbphoneclaw

```bash
cd ~/Vibecoding/adbphoneclaw
python3 -m venv venv && . venv/bin/activate
pip install -r requirements.txt        # sounddevice soundfile numpy requests pytest
export XIAOMI_MIMO_API_KEY="sua_chave" # ASR/TTS MiMo
# OLLAMA_BASE_URL / OLLAMA_MODEL opcionais (default localhost:11434, llama3.2:1b)
python main_adb.py
```
- Skills OpenClaw: `openclaw_skill_adb.py` expõe
  `phoneclaw_adb_gsm_call(to)`, `phoneclaw_adb_whatsapp_chat(to)`,
  `phoneclaw_adb_end_call()`.

## 7. OPENCLAW

- Instalar gateway OpenClaw no box.
- Config (`openclaw.json`):
  - Modelos: MiMo / OpenRouter fallback (ver MEMORY.md ordem).
  - Canais: WhatsApp/Telegram conforme necessário.
  - `contextInjection: "always"` (SOUL.md injetado).
  - SOUL/AGENTS caveman mode.
- `tools/bt_agent.py`, `tools/patch_ofono_cvsd.sh`, `tools/hfp_*.sh` copiados p/ box.

## 8. AUTOMAÇÃO / RESILIÊNCIA

- **Restart policy** (NÃO repetir erro do Temporal no homelab):
  ```bash
  docker update --restart unless-stopped <container>...   # se usar docker
  ```
  Para serviços systemd (ofono, bt-agent, pipewire, openclaw): `enabled`.
- **cron** (near-zero token, como no homelab):
  - `0 */2 * * *` healthcheck (nginx+docker) → WhatsApp.
  - `0 8 * * *` daily_checks (weather, disco, SSL, domínio) → WhatsApp.
- **monitor/set_status.py**: atualizar estado em cada ação (working/online/idle).

## 9. GOTCHAS (NÃO REPETIR — custou dias no homelab)

- **SCO dongle = RTL8761B (`0bda:8771`) só.** Ver `SCO MTU` RX > 0 no boot.
  CSR e Qualcomm integrado são incompatíveis (hardware/firmware).
- **oFono backend, NÃO native** WirePlumber (native não registra HFP).
- **CVSD patch** reaplicar após upgrade ofono.
- **ADB não desbloqueia tela** → script PIN obrigatório antes de any UI.
- **WhatsApp call não disca** → tap no botão call.
- **Voice loop só transcreve mic local**, não remoto (limitado por HFP monitor).
- **Radio BT wedge** após params SCO ruins → **reboot cura** (firmware).
  Evitar spammar `Create/Accept Synchronous Connection` com params errados.
- **Não spammar número de teste** (+351912540117) — uma call por validação.

## 10. VALIDAÇÃO (SMOKE TEST)

```bash
adb devices                              # phone "device"
hciconfig -a hciX | grep "SCO MTU"       # RX > 0
# parear + oFono Dial test:
bash tools/hfp_sco_test.sh               # Synchronous Connect Complete 0x00
pactl list sources short | grep bluez    # bluez_source handsfree presente
python main_adb.py                       # menu sobe, loop de voz ok
# OpenClaw responde no canal configurado
```

---

## ORDEM DE EXECUÇÃO

1. Montar hardware (mini PC + dongle RTL8761B + celular).
2. Instalar OS (Ubuntu 24.04).
3. Seção 3 (base) → 4 (BT/HFP) → 5 (ADB) → 6 (adbphoneclaw) → 7 (OpenClaw).
4. Seção 8 (restart/cron) → 9 (checar gotchas) → 10 (smoke test).
5. Git commit do `/docs` + scripts na box.

Próximo passo: confirmar hardware (comprar RTL8761B se não tiver) e escolher
mini PC. Eu gero scripts de bootstrap (install.sh) se quiser.

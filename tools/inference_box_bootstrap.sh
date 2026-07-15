#!/usr/bin/env bash
# inference_box_bootstrap.sh
# Instala OpenClaw + adbphoneclaw + HFP stack numa box fresh (Ubuntu 24.04).
# Rodar como root (sudo -i) numa box DEDICADA.
# Requer: dongle BT Realtek RTL8761B (0bda:8771) | celular Android com plano via USB.
# NAO usar CSR 0a12:0001 nem Qualcomm integrado (SCO nao funciona).
set -euo pipefail

USER_HOME="/home/$(logname 2>/dev/null || echo rafael)"
WORKDIR="${USER_HOME}/inference-box"
ADB_REPO="https://github.com/rafael/vibecoding.git"   # trocar por repo real do adbphoneclaw
ADB_DIR="${USER_HOME}/Vibecoding/adbphoneclaw"

echo "=== [1] apt base ==="
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y \
  android-tools-adb bluez bluez-tools ofono \
  pipewire pipewire-pulse wireplumber libspa-0.2-bluetooth \
  git curl python3 python3-venv python3-pip network-manager \
  nginx

echo "=== [2] Ollama (LLM local opcional) ==="
if command -v ollama >/dev/null 2>&1; then
  echo "ollama ja presente"
else
  curl -fsSL https://ollama.com/install.sh | sh
fi
ollama pull llama3.2:1b || true

echo "=== [3] dongle BT check (RX SCO MTU > 0) ==="
systemctl enable --now bluetooth
sleep 2
HCIS=$(hciconfig -a 2>/dev/null | grep -E "^hci" | awk '{print $1}')
RX_OK=0
for h in $HCIS; do
  RX=$(hciconfig -a "$h" 2>/dev/null | grep "SCO MTU" | awk '{print $4}' | cut -d: -f2)
  echo "$h SCO MTU RX=$RX"
  if [ "${RX:-0}" != "0" ] && [ -n "$RX" ]; then RX_OK=1; fi
done
if [ "$RX_OK" != "1" ]; then
  echo "ERRO: nenhum dongle com SCO MTU RX>0. Compre Realtek RTL8761B (0bda:8771)."
  echo "Qualcomm integrado e CSR 0a12:0001 NAO servem."
  exit 1
fi

echo "=== [4] WirePlumber conf (ofono backend, CVSD) ==="
WP_DIR="/etc/wireplumber/wireplumber.conf.d"
mkdir -p "$WP_DIR"
cat > "$WP_DIR/51-bluez-cvsd.conf" <<'EOF'
monitor.bluez.properties = {
  bluez5.hfphsp-backend = "ofono"
  bluez5.codecs = [ "cvsd" ]
  bluez5.hw-offload-sco = false
}
EOF
echo "wireplumber ofono backend set"

echo "=== [5] oFono CVSD patch ==="
if [ -x "${USER_HOME}/.openclaw/tools/patch_ofono_cvsd.sh" ]; then
  bash "${USER_HOME}/.openclaw/tools/patch_ofono_cvsd.sh"
else
  echo "AVISO: patch_ofono_cvsd.sh nao encontrado em ${USER_HOME}/.openclaw/tools/ — copie antes."
fi

echo "=== [6] bt-agent.service (auto-confirma pareamento) ==="
BT_AGENT_SRC="${WORKDIR}/tools/bt_agent.py"
if [ ! -f "$BT_AGENT_SRC" ]; then
  BT_AGENT_SRC="${USER_HOME}/.openclaw/tools/bt_agent.py"
fi
if [ -f "$BT_AGENT_SRC" ]; then
  cp "$BT_AGENT_SRC" /usr/local/bin/bt_agent.py
else
  echo "AVISO: bt_agent.py nao encontrado. Copie manual."
fi
chmod +x /usr/local/bin/bt_agent.py
cat > /etc/systemd/system/bt-agent.service <<'EOF'
[Unit]
Description=BT Agent (NoInputNoOutput auto-pair)
After=bluetooth.service
[Service]
Type=simple
ExecStart=/usr/local/bin/bt_agent.py
Restart=always
User=root
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now bt-agent
systemctl enable --now ofono

echo "=== [7] ADB + celular ==="
cat > /etc/udev/rules.d/51-android.rules <<'EOF'
SUBSYSTEM=="usb", ATTR{idVendor}=="*", MODE="0666", GROUP="plugdev"
EOF
udevadm control --reload-rules 2>/dev/null || true
echo "Conecte celular via USB, ative Depuracao USB, autorize host."
echo "Desbloquear tela (ADB nao faz): adb shell input keyevent 224; adb shell input text PIN; adb shell input keyevent 66"

echo "=== [8] adbphoneclaw ==="
mkdir -p "$(dirname "$ADB_DIR")"
if [ -d "$ADB_DIR" ]; then
  echo "adbphoneclaw ja existe: $ADB_DIR"
else
  git clone "$ADB_REPO" "$(dirname "$ADB_DIR")" 2>&1 || echo "git clone falhou — clone manual"
fi
if [ -d "$ADB_DIR" ]; then
  python3 -m venv "${ADB_DIR}/venv"
  bash -c "source ${ADB_DIR}/venv/bin/activate && pip install -r ${ADB_DIR}/requirements.txt"
  echo "adbphoneclaw instalado. Configurar XIAOMI_MIMO_API_KEY env."
fi

echo "=== [9] OpenClaw gateway ==="
curl -fsSL https://openclaw.ai/install.sh | sh 2>&1 || echo "OpenClaw install falhou — ver docs"
mkdir -p "${USER_HOME}/.openclaw/tools"
cp "${WORKDIR}/tools/patch_ofono_cvsd.sh" "${USER_HOME}/.openclaw/tools/" 2>/dev/null || true
cp "${WORKDIR}/tools/hfp_*.sh" "${USER_HOME}/.openclaw/tools/" 2>/dev/null || true
cp /usr/local/bin/bt_agent.py "${USER_HOME}/.openclaw/tools/" 2>/dev/null || true

echo "=== [10] restart policy (nao repetir erro Temporal) ==="
systemctl enable --now pipewire.service pipewire-pulse.service wireplumber.service 2>/dev/null || true
systemctl enable bluetooth ofono bt-agent 2>/dev/null || true

echo "=== [11] smoke test (manual) ==="
echo "hciconfig -a hciX | grep SCO MTU      # RX > 0"
echo "adb devices                            # phone device"
echo "bash ${USER_HOME}/.openclaw/tools/hfp_sco_test.sh   # Synchronous Connect Complete 0x00"
echo "pactl list sources short | grep bluez # bluez_source presente"
echo "cd $ADB_DIR && python main_adb.py     # menu sobe"

echo "=== FIM bootstrap ==="
echo "PROXIMO: parear celular (tipo 'Fones de ouvido' + toggle Chamadas ON), rodar smoke test."

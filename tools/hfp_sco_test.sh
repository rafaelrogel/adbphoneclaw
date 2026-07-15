#!/bin/bash
# hfp_sco_test.sh — forca SCO CVSD via host-initiated Create Synchronous Connection.
# Contorna o BlueZ que rejeita (0x0d) o eSCO que o moto insiste em pedir.
# O host (AG) inicia SCO classico CVSD; celular deve aceitar.
# Uso: bash tools/hfp_sco_test.sh [numero]
set -u
NUM="${1:-+351912540117}"
MAC=50:13:1D:F5_E6_FC
OFONO=/hfp/org/bluez/hci0/dev_50_13_1D_F5_E6_FC

echo "[1] Conectar $MAC se preciso..."
if ! bluetoothctl info "$MAC" 2>/dev/null | grep -q "Connected: yes"; then
  timeout 25 bluetoothctl connect "$MAC"
  sleep 3
fi
if ! bluetoothctl info "$MAC" 2>/dev/null | grep -q "Connected: yes"; then
  echo "FALHOU conectar. Liga BT no celular e deixa perto do PC, depois roda de novo."
  exit 1
fi

echo "[2] btmon em background..."
sudo pkill -x btmon 2>/dev/null; sleep 1
sudo stdbuf -oL btmon > /tmp/btmon_sco.log 2>&1 &
BTMON=$!
cleanup(){ sudo kill "$BTMON" 2>/dev/null; sudo dbus-send --system --print-reply --dest=org.ofono "$OFONO" org.ofono.VoiceCallManager.HangupAll >/dev/null 2>&1; }
trap cleanup EXIT

echo "[3] Dial $NUM..."
sudo dbus-send --system --print-reply --dest=org.ofono "$OFONO" org.ofono.VoiceCallManager.Dial string:"$NUM" string:"" >/dev/null

echo "[4] Aguardar call active..."
for i in $(seq 1 10); do
  sleep 2
  ST=$(sudo dbus-send --system --print-reply --dest=org.ofono "$OFONO" org.ofono.VoiceCallManager.GetCalls 2>/dev/null | grep -oP '"(active|dialing|alerting)"' | head -1)
  echo "  poll $i: $ST"
  [ "$ST" = '"active"' ] && break
done

echo "[5] ACL handle..."
H=$(hcitool con 2>/dev/null | grep -i "ACL.*$MAC" | grep -oP 'handle \K\d+')
echo "  handle=$H"
[ -z "$H" ] && { echo "Sem handle ACL"; exit 1; }
H0=$(printf "%02x" $((H & 0xff))); H1=$(printf "%02x" $((H >> 8)))

echo "[6] Create Synchronous Connection (SCO CVSD classico, pkt HV1/2/3)..."
# Connection_Handle(2) TXBW(4)=8000 RXBW(4)=8000 MaxLat(2)=0 Voice(2)=0x0060 Retx(1)=0 Pkt(2)=0x0007
sudo hcitool cmd 0x01 0x0028 0x"$H0" 0x"$H1" 0x80 0x1f 0x00 0x00 0x80 0x1f 0x00 0x00 0x00 0x00 0x60 0x00 0x00 0x07 0x00
sleep 3

echo "[7] Resultado btmon (SCO/eSCO/Status)..."
grep -iE "Synchronous Connect Complete|Link type|Status:|Accept|Reject|eSCO|SCO" /tmp/btmon_sco.log | tail -15
echo "--- bluez nodes ---"
pactl list sources short 2>/dev/null | grep -i bluez || echo "sem bluez source"
pactl list sinks short 2>/dev/null   | grep -i bluez || echo "sem bluez sink"
echo "--- fim. Call ativa; CTRL-C ou ENTER p/ hangup ---"
read || true

#!/bin/bash
# hfp_accept_sco.sh — aceita SCO do celular manualmente via HCI
# Monitora btmon por Connect Request e manda Accept Synchronous Connection Request
# Uso: bash tools/hfp_accept_sco.sh [numero]
set -u
NUM="${1:-+351912540117}"
MAC_HEX="50:13:1D:F5:E6:FC"
OFONO="/hfp/org/bluez/hci0/dev_50_13_1D_F5_E6_FC"

# 1. btmon em background
sudo pkill -x btmon 2>/dev/null; sleep 1
sudo stdbuf -oL btmon > /tmp/btmon_accept.log 2>&1 &
BTMON=$!
trap "sudo kill $BTMON 2>/dev/null; sudo dbus-send --system --print-reply --dest=org.ofono $OFONO org.ofono.VoiceCallManager.HangupAll >/dev/null 2>&1" EXIT

# 2. dial
echo "Dial $NUM..."
sudo dbus-send --system --print-reply --dest=org.ofono "$OFONO" org.ofono.VoiceCallManager.Dial string:"$NUM" string:"" >/dev/null

# 3. esperar active
echo "Esperando call active..."
for i in $(seq 1 10); do sleep 2; ST=$(sudo dbus-send --system --print-reply --dest=org.ofono "$OFONO" org.ofono.VoiceCallManager.GetCalls 2>/dev/null | grep -oP '"(active|dialing|alerting)"' | head -1); echo "  poll $i: $ST"; [ "$ST" = '"active"' ] && break; done

# 4. monitorar btmon por Connect Request e aceitar
echo "Monitorando Connect Request do celular (timeout ~20s)..."
for i in $(seq 1 40); do
    sleep 0.5
    # procurar Connect Request no btmon (celular pede SCO)
    if grep -q "Connect Request" /tmp/btmon_accept.log 2>/dev/null; then
        # verificar se ja foi aceito/rejeitado
        if grep -q "Synchronous Connect Complete" /tmp/btmon_accept.log 2>/dev/null; then
            echo "SCO Complete detectado!"
            break
        fi
        echo "Connect Request detectado! Aceitando com CVSD..."
        # Accept Synchronous Connection Request (0x01 0x0029)
        # BD_ADDR: 50 13 1D F5 E6 FC
        # TX BW: 80 1F 00 00 (8000)
        # RX BW: 80 1F 00 00 (8000)
        # Max Latency: 07 00
        # Voice Setting: 60 00 (CVSD)
        # Retx: 01
        # Packet Type: 38 00 (eSCO EV3/2-EV3/3-EV3)
        sudo hcitool cmd 0x01 0x0029 0x50 0x13 0x1D 0xF5 0xE6 0xFC 0x80 0x1f 0x00 0x00 0x80 0x1f 0x00 0x00 0x07 0x00 0x60 0x00 0x01 0x38 0x00
        sleep 3
        break
    fi
done

# 5. resultado
echo "=== btmon SCO ==="
grep -iE "Synchronous Connect Complete|Link type|Status:|Accept|Reject|eSCO|SCO|Connect Request" /tmp/btmon_accept.log | tail -15
echo "=== SCO handle? ==="
hcitool con 2>&1
echo "=== bluez nodes ==="
pactl list sources short 2>/dev/null | grep -i bluez || echo "sem bluez source"
pactl list sinks short 2>/dev/null | grep -i bluez || echo "sem bluez sink"
echo "Pressione ENTER pra hangup."
read || true

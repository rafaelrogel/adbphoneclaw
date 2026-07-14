#!/usr/bin/env bash
# Liga chamada HFP PC<->celular (moto) via oFono + roteia audio no PulseAudio.
# ORDEM CRITICA: oFono soh cria bluez_source/sink QUANDO call ativa (SCO up).
# Loopback TEM que carregar DEPOIS do device existir, senao cai no default
# (mic->speaker = feedback/eco local).
#
# Uso:
#   hfp_call.sh <numero>   -> disca e roteia apos SCO up
#   hfp_call.sh hangup     -> desliga call e REMOVE loopbacks (evita feedback)
set -u
BT_MAC=50:13:1D:F5:E6:FC
CARD=bluez_card.50_13_1D_F5_E6_FC
MODEM=/hfp/org/bluez/hci0/dev_50_13_1D_F5_E6_FC
SRC=bluez_source.50_13_1D_F5_E6_FC.handsfree_audio_gateway
SINK=bluez_sink.50_13_1D_F5_E6_FC.handsfree_audio_gateway

unload_loopbacks() {
  for m in $(pactl list short modules 2>/dev/null | awk '/loopback/{print $1}'); do
    pactl unload-module "$m" 2>/dev/null || true
  done
}

pulseaudio --start >/dev/null 2>&1 || true
sleep 1
pactl set-card-profile "$CARD" handsfree_audio_gateway 2>/dev/null || true
sleep 1

if [ "${1:-}" = "hangup" ]; then
  unload_loopbacks
  for c in $(dbus-send --system --dest=org.ofono "$MODEM" org.ofono.VoiceCallManager.GetCalls 2>/dev/null \
            | grep -oP 'object path "\K[^"]+'); do
    dbus-send --system --dest=org.ofono "$c" org.ofono.VoiceCall.Hangup >/dev/null 2>&1 || true
  done
  echo "hangup + loopbacks removidos"
  exit 0
fi

[ -z "${1:-}" ] && { echo "uso: $0 <numero|hangup>"; exit 1; }

# 1) disca (oFono cria bluez_source/sink quando SCO sobe)
dbus-send --print-reply --system --dest=org.ofono "$MODEM" org.ofono.VoiceCallManager.Dial string:"$1" string:"" 2>&1
echo "=> discando $1 ... aguardando SCO/HFP device subir"

# 2) espera bluez_source E bluez_sink aparecerem (ate 12s)
for i in $(seq 1 24); do
  src_ok=$(pactl list sources short 2>/dev/null | grep -c "$SRC")
  snk_ok=$(pactl list sinks   short 2>/dev/null | grep -c "$SINK")
  active=$(python3 - <<PY 2>/dev/null
import dbus
try:
    bus=dbus.SystemBus()
    m=dbus.Interface(bus.get_object('org.ofono','/'),'org.ofono.Manager')
    for p,pr in m.GetModems():
        vc=dbus.Interface(bus.get_object('org.ofono',p),'org.ofono.VoiceCallManager')
        for c,st in vc.GetCalls():
            if st.get('State')=='active': print('YES')
except Exception: pass
PY
)
  if [ "$src_ok" -ge 1 ] && [ "$snk_ok" -ge 1 ] && [ "$active" = "YES" ]; then
    echo "SCO up apos ${i}x0.5s"
    break
  fi
  sleep 0.5
done

# 3) carrega loopbacks SOH agora (devices existem)
unload_loopbacks
pactl load-module module-loopback source="$SRC" sink=@DEFAULT_SINK@ latency_msec=20 >/dev/null && echo "loopback remoto->speaker OK"
pactl load-module module-loopback source=@DEFAULT_SOURCE@ sink="$SINK" latency_msec=20 >/dev/null && echo "loopback mic->phone OK"
echo "=> pronto: tu ouves o outro lado; fone recomendado p/ evitar eco"

#!/usr/bin/env bash
# Chamada HFP via PipeWire (nativo, sem oFono).
# PipeWire expoe API de telefonia: org.pipewire.Telephony (oFono-compat).
# O audio SCO (nos bluez_input/bluez_output) soh aparece quando call ACTIVE.
# Loopback soh carrega DEPOIS dos nos existirem.
#
# Uso:
#   pw_call.sh <numero>   -> disca e roteia apos call active
#   pw_call.sh hangup      -> desliga e remove loopbacks
set -u
AG=/org/pipewire/Telephony/ag1
SVC=org.pipewire.Telephony
IFACE=org.pipewire.Telephony.AudioGateway1

unload_loopbacks() {
  for m in $(pactl list short modules 2>/dev/null | awk '/loopback/{print $1}'); do
    pactl unload-module "$m" 2>/dev/null || true
  done
}

if [ "${1:-}" = "hangup" ]; then
  busctl --user call "$SVC" "$AG" "$IFACE" HangupAll >/dev/null 2>&1 || true
  unload_loopbacks
  echo "hangup + loopbacks removidos"
  exit 0
fi

[ -z "${1:-}" ] && { echo "uso: $0 <numero|hangup>"; exit 1; }

busctl --user call "$SVC" "$AG" "$IFACE" Dial s "$1" 2>&1
echo "=> discando $1 ... aguardando call ACTIVE (SCO)"

# poll: State==active E nos bluez presentes
for i in $(seq 1 60); do
  st=$(busctl --user get-property "$SVC" "$AG" org.pipewire.Telephony.AudioGatewayTransport1 State 2>/dev/null | tr -d '"' | awk '{print $2}')
  cap=$(pactl list short sources 2>/dev/null | awk '{print $2}' | grep -i bluez | head -1)
  pbk=$(pactl list short sinks   2>/dev/null | awk '{print $2}' | grep -i bluez | head -1)
  if [ "$st" = "active" ] && [ -n "$cap" ] && [ -n "$pbk" ]; then
    echo "call ACTIVE apos ${i}s | cap=$cap pbk=$pbk"
    break
  fi
  sleep 0.5
done

if [ -z "${cap:-}" ] || [ -z "${pbk:-}" ]; then
  echo "AVISO: call nao ficou active ou nos bluez nao apareceram (call nao atendida?)."
  exit 2
fi

# roteia: remoto(cap)->speakers ; mic->phone(pbk)
unload_loopbacks
pactl load-module module-loopback source="$cap" sink=@DEFAULT_SINK@ latency_msec=20 >/dev/null && echo "loopback remoto->speaker OK"
pactl load-module module-loopback source=@DEFAULT_SOURCE@ sink="$pbk" latency_msec=20 >/dev/null && echo "loopback mic->phone OK"
echo "=> pronto: fala. fone recomendado p/ evitar eco. hangup: $0 hangup"

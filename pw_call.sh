#!/usr/bin/env bash
# Chamada HFP via PipeWire nativo (org.pipewire.Telephony). Sem oFono.
# NOTAS:
#  - Codec forcado CVSD (wireplumber drop-in 51-bluez-cvsd.conf); mSBC falha SCO.
#  - Transport.State property MENTE (fica "pending"); detectar atendimento via
#    VoiceCallManager.GetCalls -> call State=active.
#  - Ao atender, nos bluez_input/bluez_output aparecem sozinhos (SCO up). Loopback depois.
#
# Uso:
#   pw_call.sh <numero>   -> disca, roteia audio ao atender
#   pw_call.sh hangup     -> desliga + remove loopbacks
set -u
SVC=org.pipewire.Telephony
AG=/org/pipewire/Telephony/ag1
AGI=org.pipewire.Telephony.AudioGateway1
VCM=org.ofono.VoiceCallManager

unload_loopbacks() {
  for m in $(pactl list short modules 2>/dev/null | awk '/loopback/{print $1}'); do
    pactl unload-module "$m" 2>/dev/null || true
  done
}
call_active() { busctl --user call "$SVC" "$AG" "$VCM" GetCalls 2>/dev/null | grep -q '"State" s "active"'; }
call_gone()   { busctl --user call "$SVC" "$AG" "$VCM" GetCalls 2>/dev/null | grep -q 'a{oa{sv}} 0'; }

if [ "${1:-}" = "hangup" ]; then
  busctl --user call "$SVC" "$AG" "$AGI" HangupAll >/dev/null 2>&1 || true
  unload_loopbacks
  echo "hangup + loopbacks removidos"
  exit 0
fi

[ -z "${1:-}" ] && { echo "uso: $0 <numero|hangup>"; exit 1; }

busctl --user call "$SVC" "$AG" "$AGI" Dial s "$1" >/dev/null 2>&1
echo "=> discando $1 ... atende no moto"

# espera atender (call State=active)
answered=0
for i in $(seq 1 90); do
  if call_active; then echo "atendido apos ${i}s"; answered=1; break; fi
  if call_gone;   then echo "call encerrada (nao atendeu/rejeitou)"; unload_loopbacks; exit 2; fi
  sleep 1
done
[ "$answered" = 0 ] && { echo "timeout"; unload_loopbacks; exit 2; }

# espera nos bluez (SCO sobe ao atender com CVSD)
cap=""; pbk=""
for i in $(seq 1 20); do
  cap=$(pactl list short sources 2>/dev/null | awk '{print $2}' | grep -i bluez | head -1)
  pbk=$(pactl list short sinks   2>/dev/null | awk '{print $2}' | grep -i bluez | head -1)
  [ -n "$cap" ] && [ -n "$pbk" ] && break
  sleep 0.5
done
if [ -z "$cap" ] || [ -z "$pbk" ]; then
  echo "AVISO: nos bluez nao apareceram. Codec=$(busctl --user get-property $SVC $AG org.pipewire.Telephony.AudioGatewayTransport1 Codec 2>/dev/null)"
  echo "ver: journalctl --user -u wireplumber -n 30 | grep -i sco"
  exit 3
fi
echo "nos: cap=$cap pbk=$pbk"

# roteia
unload_loopbacks
pactl load-module module-loopback source="$cap" sink=@DEFAULT_SINK@ latency_msec=30 >/dev/null && echo "loopback remoto->speaker OK"
pactl load-module module-loopback source=@DEFAULT_SOURCE@ sink="$pbk" latency_msec=30 >/dev/null && echo "loopback mic->phone OK"
echo "=> audio roteado (CVSD). fala. hangup: $0 hangup"

#!/usr/bin/env bash
# Discagem HFP via PipeWire nativo (org.pipewire.Telephony). Sem oFono.
# Modo agente: soh disca e aguarda atendimento. O roteamento de audio
# (captura/playback) fica por conta do main_adb.py via pw-record/pw-play
# usando os node IDs retornados por pw-dump (ver tools/voice_agent.py).
# Uso:
#   pw_call.sh <numero>   -> disca, aguarda atendimento, imprime "ANSWERED"
#   pw_call.sh hangup     -> desliga
set -u
SVC=org.pipewire.Telephony
AG=/org/pipewire/Telephony/ag1
AGI=org.pipewire.Telephony.AudioGateway1
VCM=org.ofono.VoiceCallManager

call_active() { busctl --user call "$SVC" "$AG" "$VCM" GetCalls 2>/dev/null | grep -q '"State" s "active"'; }
call_gone()   { busctl --user call "$SVC" "$AG" "$VCM" GetCalls 2>/dev/null | grep -q 'a{oa{sv}} 0'; }

if [ "${1:-}" = "hangup" ]; then
  busctl --user call "$SVC" "$AG" "$AGI" HangupAll >/dev/null 2>&1 || true
  echo "hangup enviado"
  exit 0
fi

NUM="${1:-}"
[ -z "$NUM" ] && { echo "uso: $0 <numero|hangup>"; exit 1; }

busctl --user call "$SVC" "$AG" "$AGI" Dial s "$NUM" >/dev/null 2>&1
echo "=> discando $NUM ... atende no moto"

answered=0
for i in $(seq 1 90); do
  if call_active; then echo "ANSWERED"; answered=1; break; fi
  # NOTA: logo apos Dial, GetCalls retorna 'a{oa{sv}} 0' (call ainda
  # nao criado) -> call_gone falsamente positivo. Por isso NAO checamos
  # call_gone aqui; soh esperamos call_active ou timeout.
  sleep 1
done
[ "$answered" = 0 ] && { echo "timeout"; exit 2; }
exit 0

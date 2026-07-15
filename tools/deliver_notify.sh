#!/bin/bash
# Notifica Rafael no WhatsApp quando o deliver_whatsapp.py terminar.
ROOT=/home/rafael/.openclaw/workspace
LOG=$ROOT/tools/deliver_whatsapp.log
OPENCLAW=/home/rafael/.nvm/versions/node/v24.16.0/bin/openclaw
TARGET=+351910070509
NOTIFIED=$ROOT/output/.notify_done
for i in $(seq 1 800); do
  cnt=$(grep -c "sent song" "$LOG" 2>/dev/null || echo 0)
  if [ "$cnt" -ge 40 ]; then
    [ -f "$NOTIFIED" ] || { "$OPENCLAW" message send --channel whatsapp --target "$TARGET" --message "✅ Todos 40 mp3 do producer enviados via zap (song_00..39)."; touch "$NOTIFIED"; }
    break
  fi
  if ! pgrep -f deliver_whatsapp.py >/dev/null; then
    [ -f "$NOTIFIED" ] || { "$OPENCLAW" message send --channel whatsapp --target "$TARGET" --message "⚠️ Envio parou em $cnt/40. Checa tools/deliver_whatsapp.log"; touch "$NOTIFIED"; }
    break
  fi
  sleep 15
done

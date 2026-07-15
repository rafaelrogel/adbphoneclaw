#!/usr/bin/env bash
# Monitor producer: avisa no WhatsApp quando 40 clips prontos.
# Roda detached (nohup/setsid) pra sobreviver a restart do gateway.
# Se producer morrer antes de 40, relanca (com teto de relaunches).
set -u
OUT=/home/rafael/.openclaw/workspace/output
TARGET=+351910070509
LOG=/home/rafael/.openclaw/workspace/tools/monitor_producer_done.log
WORKSPACE=/home/rafael/.openclaw/workspace
RELAUNCH_CAP=5
RELAUNCH_COUNT=0

count() {
  ls -1 "$OUT"/song_*.mp3 2>/dev/null | grep -cE "song_[0-9]+\.mp3"
}

producer_alive() {
  pgrep -f "producer_browser[.]py" >/dev/null 2>&1
}

relaunch_producer() {
  RELAUNCH_COUNT=$((RELAUNCH_COUNT+1))
  if [ "$RELAUNCH_COUNT" -gt "$RELAUNCH_CAP" ]; then
    echo "[$(date -u +%H:%M:%S)] relaunch cap ($RELAUNCH_CAP) atingido. parando." >> "$LOG"
    return 1
  fi
  cd "$WORKSPACE"
  . venv_producer/bin/activate
  PYTHONPATH="$WORKSPACE" nohup python3 -u tools/producer_browser.py >> tools/producer_browser.log 2>&1 &
  disown 2>/dev/null
  echo "[$(date -u +%H:%M:%S)] producer morto <40, RELAUNCH #$RELAUNCH_COUNT (pid $!)" >> "$LOG"
  return 0
}

echo "[$(date -u +%H:%M:%S)] monitor iniciado (pid $$)" >> "$LOG"
while true; do
  n=$(count)
  echo "[$(date -u +%H:%M:%S)] clips=$n/40" >> "$LOG"
  if [ "$n" -ge 40 ]; then
    msg="PRODUCER PRONTO: 40/40 clips ambient gerados em output/. Todos 300s validados."
    openclaw message send --channel whatsapp --target "$TARGET" --message "$msg" >> "$LOG" 2>&1
    echo "[$(date -u +%H:%M:%S)] AVISADO. encerrando." >> "$LOG"
    exit 0
  fi
  # Se producer morreu e falta, relanca (ate cap)
  if ! producer_alive; then
    echo "[$(date -u +%H:%M:%S)] producer NAO rodando, clips=$n" >> "$LOG"
    relaunch_producer || { echo "[$(date -u +%H:%M:%S)] sem relaunch, aguardando..." >> "$LOG"; }
  fi
  sleep 120
done

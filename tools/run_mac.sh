#!/usr/bin/env bash
# Start Video Director on your own computer.
#   tools/run_mac.sh              this computer only: http://127.0.0.1:8765/studio
#   tools/run_mac.sh --lan        also your iPhone on the same Wi-Fi (asks for an access code; the code is printed once)
#   tools/run_mac.sh --real-ai    allow the real Claude worker (it still spends nothing until you set an AI budget in the app)
# Paid narration, paid pictures and paid video stay locked whatever you pass here. Ctrl-C stops it (and any drawing in progress).
set -eu
D=$(cd "$(dirname "$0")/.." && pwd); PORT=${VD_PORT:-8765}; LAN=; REAL=
for a in "$@"; do case "$a" in --lan) LAN=--lan;; --real-ai) REAL=1;; *) echo "unknown option $a"; exit 2;; esac; done
command -v ffmpeg >/dev/null || { echo "ffmpeg is needed: brew install ffmpeg"; exit 1; }
export PYTHONPATH="$D" VIDEO_DIRECTOR_PAID_ENABLED=0
[ -n "$REAL" ] && export VD_AI_REAL_ENABLED=1 || unset VD_AI_REAL_ENABLED
if [ -n "$LAN" ]; then
  ip=$(ipconfig getifaddr en0 2>/dev/null || hostname -I 2>/dev/null | awk '{print $1}')
  echo "On your iPhone (same Wi-Fi): http://$ip:$PORT/studio"
fi
PY=python3; [ -x "$D/.venv/bin/python" ] && PY="$D/.venv/bin/python"     # made by tools/setup_mac.sh
cd "$D" && exec "$PY" -m director.dashboard.serve --port "$PORT" $LAN

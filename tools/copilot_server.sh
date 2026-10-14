#!/usr/bin/env bash
# Co-Pilot Studio server on an isolated folder.  tools/copilot_server.sh fresh|restart PORT VAR [SEED_VAR]
# fresh: new folder (copy of SEED_VAR if given, else an empty studio) with the dashboard media linked read-only;
# restart: same folder, new process (the Co-Pilot resumes running projects by itself).
set -u
D=$(cd "$(dirname "$0")/.." && pwd); PORT=$2; V=$3; SEED=${4:-}
ps -eo pid,comm,args | awk -v p="--port $PORT" '$2=="python3" && index($0,"dashboard.serve " p) {print $1}' | xargs -r kill
sleep 1
if [ "$1" = fresh ]; then
  [ -e "$V" ] && { echo "refusing to reuse $V: give a new folder"; exit 1; }
  if [ -n "$SEED" ]; then cp -a "$SEED" "$V"; else mkdir -p "$V"; fi
  [ -e "$V/media" ] || ln -s "$D/var/dashboard/media" "$V/media"
  [ -e "$V/events.sqlite" ] || cp "$D/var/dashboard/events.sqlite" "$V/events.sqlite"
fi
(cd "$D" && env -u ELEVENLABS_API_KEY -u FAL_KEY VIDEO_DIRECTOR_PAID_ENABLED=0 VD_STUDIO_TEST=1 VD_DASHBOARD_VAR="$V" PYTHONPATH="$D" \
   ${VD_DRAFT_VOICE:+VD_DRAFT_VOICE=$VD_DRAFT_VOICE} nohup python3 -m director.dashboard.serve --port "$PORT" >> "$V/serve.log" 2>&1 &)
for i in $(seq 1 120); do curl -sf -o /dev/null "http://127.0.0.1:$PORT/studio" && exit 0; sleep 0.5; done; echo "server did not start"; tail -20 "$V/serve.log"; exit 1

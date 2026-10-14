#!/usr/bin/env bash
# UAT server on an isolated copy of the dashboard log.  tools/uat_server.sh fresh|restart [PORT]
# fresh: new copy of var/dashboard/events.sqlite (the studio starts empty); restart: same copy, new process.
set -u
D=$(cd "$(dirname "$0")/.." && pwd); PORT=${2:-8767}; V=$D/var/dashboard-uat
ps -eo pid,comm,args | awk -v p="--port $PORT" '$2=="python3" && index($0,"dashboard.serve " p) {print $1}' | xargs -r kill
sleep 1
if [ "$1" = fresh ]; then rm -rf "$V" "$D/var/uat/results.json" "$D/var/uat/pid"; mkdir -p "$V" "$D/var/uat"; cp "$D/var/dashboard/events.sqlite" "$V/"; cp -a "$D/var/dashboard/media" "$V/media"; fi
(env -u ELEVENLABS_API_KEY -u FAL_KEY VIDEO_DIRECTOR_PAID_ENABLED=0 VD_STUDIO_TEST=1 VD_DASHBOARD_VAR="$V" PYTHONPATH="$D" nohup python3 -m director.dashboard.serve --port "$PORT" >> "$D/var/uat/serve.log" 2>&1 &)
for i in $(seq 1 60); do curl -sf -o /dev/null "http://127.0.0.1:$PORT/studio" && exit 0; sleep 0.5; done; echo "server did not start"; exit 1

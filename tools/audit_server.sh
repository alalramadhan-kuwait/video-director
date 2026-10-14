#!/usr/bin/env bash
# The independent auditor's own copy of the finished UAT state, on port 8768.  tools/audit_server.sh fresh|restart
set -u
D=$(cd "$(dirname "$0")/.." && pwd); V=$D/var/audit/var; PORT=8768
ps -eo pid,comm,args | awk -v p="--port $PORT" '$2=="python3" && index($0,"dashboard.serve " p) {print $1}' | xargs -r kill
sleep 1
if [ "$1" = fresh ]; then
  if [ -d "$V" ]; then find "$V" -type f -exec chmod u+w {} +; rm -rf "$V"; fi
  mkdir -p "$V" "$D/var/audit/shots"; cp "$D/var/dashboard-uat/events.sqlite" "$V/"; cp -r "$D/var/dashboard-uat/studio" "$V/studio"
  find "$V/studio" -type f -exec chmod u+w {} +; cp -a "$D/var/dashboard/media" "$V/media"
  [ -f "$D/var/dashboard-uat/ledger.sqlite" ] && cp "$D/var/dashboard-uat/ledger.sqlite" "$V/"
fi
(env -u ELEVENLABS_API_KEY -u FAL_KEY VIDEO_DIRECTOR_PAID_ENABLED=0 VD_STUDIO_TEST=1 VD_DASHBOARD_VAR="$V" PYTHONPATH="$D" nohup python3 -m director.dashboard.serve --port $PORT >> "$D/var/audit/serve.log" 2>&1 &)
for i in $(seq 1 60); do curl -sf -o /dev/null "http://127.0.0.1:$PORT/studio" && exit 0; sleep 0.5; done; echo "audit server did not start"; exit 1

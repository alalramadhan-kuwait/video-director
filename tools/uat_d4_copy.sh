#!/usr/bin/env bash
# The seek-is-not-listening test (D4) on a DISPOSABLE copy of the finished UAT project (it switches the hook there).
set -u
D=$(cd "$(dirname "$0")/.." && pwd); cd "$D"; PORT=8769; V=$D/var/uat-d4/var
ps -eo pid,args | awk -v p="--port $PORT" 'index($0,"dashboard.serve " p) {print $1}' | xargs -r kill; sleep 1
rm -rf var/uat-d4; mkdir -p "$V"; cp -a var/dashboard-uat/. "$V/"; cp var/uat/pid var/uat-d4/pid
(env -u ELEVENLABS_API_KEY -u FAL_KEY VIDEO_DIRECTOR_PAID_ENABLED=0 VD_DASHBOARD_VAR="$V" PYTHONPATH="$D" nohup python3 -m director.dashboard.serve --port $PORT > var/uat-d4/serve.log 2>&1 &)
for i in $(seq 1 60); do curl -sf -o /dev/null "http://127.0.0.1:$PORT/studio" && break; sleep 0.5; done
node tools/uat_rolex.mjs http://127.0.0.1:$PORT var/uat-d4 D4
ps -eo pid,args | awk -v p="--port $PORT" 'index($0,"dashboard.serve " p) {print $1}' | xargs -r kill

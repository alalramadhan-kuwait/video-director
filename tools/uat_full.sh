#!/usr/bin/env bash
# The whole Rolex Oyster UAT from a fresh copy: UI journey, a server kill in the middle of the draft voice, then the
# disposable defect copy. Output: var/uat/ (results.json, shots/, defects/).
set -u
D=$(cd "$(dirname "$0")/.." && pwd); cd "$D"
B=http://127.0.0.1:8767
rm -rf var/uat/shots var/uat/defects; mkdir -p var/uat
tools/uat_server.sh fresh || exit 1
node tools/uat_rolex.mjs $B var/uat A B C D
echo "== killing the server in the middle of the draft voice"
tools/uat_server.sh restart
node tools/uat_rolex.mjs $B var/uat D2 DW D3 E F2 G H H2 R I J K Z
echo "== seek test on a disposable copy"
tools/uat_d4_copy.sh
echo "== defect copy"
env -u ELEVENLABS_API_KEY VIDEO_DIRECTOR_PAID_ENABLED=0 PYTHONPATH="$D" python3 tools/uat_defects.py var/dashboard-uat "$(cat var/uat/pid)" var/uat/defects
echo "== UAT FINISHED"

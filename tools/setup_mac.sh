#!/usr/bin/env bash
# One-time setup on a Mac with Homebrew. Installs free, local tools only; asks for no API key and stores none.
#   python (numpy, pyyaml, gTTS for the free draft voice, faster-whisper for word timing), node + playwright-core and
#   its Chromium (draws the scenes), ffmpeg (sound and film).
set -eu
command -v brew >/dev/null || { echo "Install Homebrew first: https://brew.sh"; exit 1; }
brew list python@3.11 >/dev/null 2>&1 || brew install python@3.11
for f in node ffmpeg; do command -v $f >/dev/null || brew install $f; done
PY=$(brew --prefix python@3.11)/bin/python3.11
D=$(cd "$(dirname "$0")/.." && pwd)
$PY -m venv "$D/.venv"
"$D/.venv/bin/pip" install --quiet numpy pyyaml gTTS faster-whisper imageio-ffmpeg
npm install --silent --prefix "$HOME/.cache/paper-story" playwright-core
(cd "$HOME/.cache/paper-story" && npx --yes playwright-core install chromium)
"$D/.venv/bin/python" "$D/vendor/paper-story/scripts/make-sfx.py"          # the paper sounds are made locally, not downloaded
[ -f "$D/vendor/paper-story/tk-logo-512.png" ] || echo "note: vendor/paper-story/tk-logo-512.png (Time Keeper logo) is not in the repo: copy it from the bundle"
echo "Ready. Start it with: tools/run_mac.sh   (or tools/run_mac.sh --lan for your iPhone)"

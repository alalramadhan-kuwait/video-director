#!/usr/bin/env bash
# Read a film's narration with OmniVoice on your own Mac, one take per line (free, local; the model is CC-BY-NC, so the
# takes are for review, not for publishing).
#   tools/voice_mac.sh films/panerai.yaml            all lines that have no take yet
#   tools/voice_mac.sh films/panerai.yaml l5,l9      read only these lines again (their old takes are moved aside, kept)
# The takes land in var/voice/<film>/ ; send that folder back, or make the film here:
#   python3 tools/make_film.py films/<film>.yaml <out> --voice-dir var/voice/<film>
set -eu
D=$(cd "$(dirname "$0")/.." && pwd); FILM=${1:?usage: tools/voice_mac.sh films/<name>.yaml [line ids]}; ONLY=${2:-}
NAME=$(basename "$FILM" .yaml); OUT="$D/var/voice/$NAME"; VENV="$D/var/omnivoice-venv"
if [ ! -x "$VENV/bin/python" ]; then
  PY=$(command -v python3.12 || true)
  [ -n "$PY" ] || { echo "Python 3.12 is needed once: brew install python@3.12"; exit 1; }
  echo "First run: installing OmniVoice in $VENV (several GB with the model; once only)"
  "$PY" -m venv "$VENV"
  "$VENV/bin/python" -m pip install -q -r "$D/skills/arabic-narration/scripts/requirements-omnivoice.txt" pyyaml
fi
mkdir -p "$OUT"
if [ -n "$ONLY" ]; then                                       # a line read again: the old take is kept, renamed
  stamp=$(date +%Y%m%d-%H%M%S)
  for id in ${ONLY//,/ }; do
    for ext in wav json; do [ -e "$OUT/$id.$ext" ] && mv "$OUT/$id.$ext" "$OUT/old-$stamp-$id.$ext.bak"; done
  done
fi
cd "$D"
PYTHONPATH="$D" "$VENV/bin/python" tools/voice_script.py "$FILM" "$OUT/script.json"
"$VENV/bin/python" skills/arabic-narration/scripts/omnivoice_narrate.py --script "$OUT/script.json" --lines-dir "$OUT" \
  --brand brand/timekeeper.json ${ONLY:+--only "$ONLY"}
echo; echo "Done: $OUT"
echo "Send me that folder (zip it), or make the film here: python3 tools/make_film.py $FILM var/film-$NAME --voice-dir $OUT"

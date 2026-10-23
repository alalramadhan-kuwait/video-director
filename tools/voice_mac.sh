#!/usr/bin/env bash
# Read a film's narration on your own Mac, one take per line (free and local; nothing is sent anywhere).
#   tools/voice_mac.sh films/panerai.yaml                    OmniVoice (CC-BY-NC model: for review, not for publishing)
#   tools/voice_mac.sh --engine voxcpm2 films/panerai.yaml   VoxCPM2 (Apache-2.0 model: may be published)
#   tools/voice_mac.sh films/panerai.yaml l5,l9              read only these lines again (old takes are renamed, kept)
#   tools/voice_mac.sh --compare films/panerai.yaml          three test lines with both voices, to choose by ear
# Each engine installs itself on its first run (Python 3.12, several GB with its model; once only).
# The takes land in var/voice/<film>-<engine>/ ; send that folder back, or make the film here:
#   python3 tools/make_film.py films/<film>.yaml <out> --voice-dir var/voice/<film>-<engine>
set -eu
D=$(cd "$(dirname "$0")/.." && pwd); ENGINE=omnivoice; COMPARE=
while [ $# -gt 0 ]; do case "$1" in
  --engine) ENGINE=${2:?--engine omnivoice|voxcpm2}; shift 2;;
  --compare) COMPARE=1; shift;;
  *) break;;
esac; done
FILM=${1:?usage: tools/voice_mac.sh [--engine omnivoice|voxcpm2] [--compare] films/<name>.yaml [line ids]}; ONLY=${2:-}
case "$ENGINE" in omnivoice|voxcpm2) ;; *) echo "unknown engine $ENGINE (omnivoice or voxcpm2)"; exit 2;; esac
NAME=$(basename "$FILM" .yaml)

setup() {                                                    # one environment per engine, made once
  local venv="$D/var/$1-venv" req="$D/skills/arabic-narration/scripts/requirements-$1.txt"
  if [ ! -x "$venv/bin/python" ]; then
    local py; py=$(command -v python3.12 || true)
    [ -n "$py" ] || { echo "Python 3.12 is needed once: brew install python@3.12" >&2; exit 1; }
    command -v ffmpeg >/dev/null || { echo "ffmpeg is needed once: brew install ffmpeg" >&2; exit 1; }
    echo "First run of $1: installing it in $venv (several GB with the model; once only)" >&2
    "$py" -m venv "$venv" >&2
    "$venv/bin/python" -m pip install -q -r "$req" pyyaml >&2
  fi
  echo "$venv/bin/python"
}

read_lines() {                                               # engine, folder, ids
  local py; py=$(setup "$1") || exit 1
  mkdir -p "$2"
  if [ -n "$3" ] && [ -z "$COMPARE" ]; then                  # a line read again: the old take is kept, renamed
    local stamp; stamp=$(date +%Y%m%d-%H%M%S)
    for id in ${3//,/ }; do
      for ext in wav json; do if [ -e "$2/$id.$ext" ]; then mv "$2/$id.$ext" "$2/old-$stamp-$id.$ext.bak"; fi; done
    done
  fi
  (cd "$D" && PYTHONPATH="$D" "$py" tools/voice_script.py "$FILM" "$2/script.json" &&
   "$py" skills/arabic-narration/scripts/omnivoice_narrate.py --engine "$1" --script "$2/script.json" --lines-dir "$2" \
     --brand brand/timekeeper.json ${3:+--only "$3"})
}

if [ -n "$COMPARE" ]; then
  IDS=${ONLY:-l1,l3,l13}                                     # the hook, a foreign name, a year said in words
  for e in omnivoice voxcpm2; do read_lines "$e" "$D/var/voice/compare-$NAME/$e" "$IDS"; done
  echo; echo "Listen and compare (the same lines, both voices): $D/var/voice/compare-$NAME/"
  echo "Then tell me which voice to use for the film."
  exit 0
fi
OUT="$D/var/voice/$NAME-$ENGINE"
read_lines "$ENGINE" "$OUT" "$ONLY"
echo; echo "Done: $OUT"
echo "Send me that folder (zip it), or make the film here: python3 tools/make_film.py $FILM var/film-$NAME --voice-dir $OUT"

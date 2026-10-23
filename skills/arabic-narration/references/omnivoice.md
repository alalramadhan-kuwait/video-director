# OmniVoice local narration

Use when the user selects OmniVoice or requests a local alternative to the gTTS timing voice.
This is the chat/plugin production path; it does not change the Studio dashboard's gTTS provider or its paid final-voice gate.

## License and routing

Code: Apache-2.0. The upstream pretrained checkpoint is **CC-BY-NC**, according to its
[model card](https://huggingface.co/k2-fsa/OmniVoice#license). Keep its output for non-commercial review;
do not describe it as a commercially cleared Time Keeper final voice. Do not silently fall back to a paid API.

Use voice design by default; no person's recording is needed. For this helper, `--instruct` is a description
of speaker attributes, not narration. The approved script is passed separately, unchanged. Existing Fasih-specific
phoneme selection, respelling workarounds, and reference settings do not automatically apply to OmniVoice.

## Install once in an isolated environment

Python 3.12 is recommended for the pinned PyTorch wheels on Apple Silicon. From the repository root:

```sh
python3.12 -m venv var/omnivoice-venv
var/omnivoice-venv/bin/python -m pip install -r skills/arabic-narration/scripts/requirements-omnivoice.txt
```

An installed plugin can put the environment and model cache in a writable work directory instead.
The first generation downloads model weights; leave several GB available. No API key is required.
Keep the heavy dependencies out of the app's ordinary environment.

## Generate a complete review take

Paths below are relative to the installed `arabic-narration` skill directory. Input may be UTF-8 text,
a JSON list of `{id, text}` records, or an object with `lines` (strings or records).

```sh
/path/to/omnivoice-venv/bin/python scripts/omnivoice_narrate.py \
  --script /path/to/approved-script.json --output /path/to/new-take.wav --plan
/path/to/omnivoice-venv/bin/python scripts/omnivoice_narrate.py \
  --script /path/to/approved-script.json --output /path/to/new-take.wav
```

Pass `--brand <repo>/brand/timekeeper.json` to use the brand's voice description and its watch-name
pronunciations (the voice is given the spoken forms; captions keep the script). The default language is `arb` (Standard Arabic); upstream does not recognize the generic name `Arabic`.
`--plan` needs only standard Python and downloads nothing. Auto device selection prefers CUDA, then Apple MPS,
then CPU. Override with `--device cpu` if needed. The helper uses the model's natural speed (1.0), generates
one narration request to reduce speaker changes, and saves a candidate WAV plus JSON provenance with hashes,
settings and measured duration. Existing files cannot be replaced. A seed records the request, but does not
promise bit-identical output across devices.

## VoxCPM2: the voice that may be published

`--engine voxcpm2` reads with [openbmb/VoxCPM2](https://huggingface.co/openbmb/VoxCPM2): Apache-2.0 weights
(commercial use permitted), Arabic among its 30 languages, 48 kHz. The brand's speaker description is given as its
documented voice-design prefix «(description)text». Its own environment: `requirements-voxcpm2.txt`. The project
documents CUDA; on Apple Silicon it is tried on MPS and may be slow; listen before trusting it. Choose by ear:
`tools/voice_mac.sh --compare films/<name>.yaml` reads three test lines (the hook, a foreign name, a year in words)
with both engines into `var/voice/compare-<name>/`.

## A film's narration, one take per line

For a film file (`films/<name>.yaml`), read each line as its own take so a wrong line can be read again alone and
the film can use the takes directly. On the owner's Mac, from the repository root, one command does it all (it
installs the environment on the first run):

```sh
tools/voice_mac.sh films/panerai.yaml            # every line without a take, into var/voice/panerai-omnivoice/
tools/voice_mac.sh --engine voxcpm2 films/panerai.yaml   # the same with VoxCPM2 (may be published)
tools/voice_mac.sh films/panerai.yaml l5,l9      # read these lines again (old takes are renamed, kept)
```

Underneath: `tools/voice_script.py` writes the lines as the voice reads them (`say`, years as words), and
`omnivoice_narrate.py --lines-dir DIR` reads each line with the same seed and speaker description, keeping any
take already in DIR. The film is then made from those takes, unchanged in speed, each listened to by Whisper:
`python3 tools/make_film.py films/<name>.yaml <out> --voice-dir DIR`. The film and its `credits.txt` are labelled
«OmniVoice REVIEW take (CC-BY-NC model) — for review, not for publishing».

Listen to the entire take, especially foreign names, omissions and repetitions. Present the full audio for
owner approval; successful synthesis is not a pronunciation or naturalness verdict. If it exceeds the film's
target length, propose a shorter script or longer film. Do not time-stretch the take to force a duration.
No automatic retries: inspect a failed or rejected take before generating a new version.

Upstream API: https://github.com/k2-fsa/OmniVoice#python-api

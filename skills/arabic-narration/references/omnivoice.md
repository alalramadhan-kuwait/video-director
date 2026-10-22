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

`--plan` needs only standard Python and downloads nothing. Auto device selection prefers CUDA, then Apple MPS,
then CPU. Override with `--device cpu` if needed. The helper uses the model's natural speed (1.0), generates
one narration request to reduce speaker changes, and saves a candidate WAV plus JSON provenance with hashes,
settings and measured duration. Existing files cannot be replaced. A seed records the request, but does not
promise bit-identical output across devices.

Listen to the entire take, especially foreign names, omissions and repetitions. Present the full audio for
owner approval; successful synthesis is not a pronunciation or naturalness verdict. If it exceeds the film's
target length, propose a shorter script or longer film. Do not time-stretch the take to force a duration.
No automatic retries: inspect a failed or rejected take before generating a new version.

Upstream API: https://github.com/k2-fsa/OmniVoice#python-api

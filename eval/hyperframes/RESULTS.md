# HyperFrames evaluation · Diabetes ep7 scene a3 (13.0 s)

Isolated: installed locally in scratchpad/eval/hf-run (npm, no install scripts), telemetry off
(HYPERFRAMES_NO_TELEMETRY=1, DO_NOT_TRACK=1), no API keys in the environment, nothing installed globally,
production untouched. Inputs identical to our engine: approved narration l4/l5, their word timings, ep7 palette, Cairo + IBM Plex Sans Arabic.

| Check | Result |
|---|---|
| Arabic shaping, RTL order, punctuation | correct (joined letters, colon/full stop at the left end) |
| Word-synced captions + highlighted words | same behaviour as ours |
| Narration sync vs published render | 0.000 s cross-correlation lag |
| `hyperframes check` | caught the chart's y-axis label overflowing the card (RTL); the same defect our art reviewer found in the published ep7 («المفعو») |
| `hyperframes lint` | caught a seek bug (repeated fromTo without baseline) |
| Render time, 13 s 1080x1920 | 44 s (1 worker, screenshot) · 20 s (4 workers, beginframe, headless shell) |
| Our engine, same machine class | about 1x real time with 4 workers (68.8 s part in ~66 s) |
| Repeatability | frames from two render modes identical (mean diff 0.00-0.03/255) |
| Size | 1.1 MB for 13 s (CRF 16 "looks") |

Not recreated: our paper-cut wave background and EP drawing library (characters, sugar bar style); that is our design code, not a limit of the tool.

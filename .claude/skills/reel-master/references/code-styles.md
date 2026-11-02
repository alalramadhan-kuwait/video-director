# Building a Reel in one of the 66 code-film styles (lemo-opuscar)

The Lemo-Opuscar library (github.com/lemomo-ai/lemo-opuscar, MIT) is a toolbox of film styles made in code: every
frame is a canvas/WebGL page rendered frame by frame; no video generation. The style list is in
`style-library.md` §B. The story, the voice and the owner's rules come from this skill as usual; only the pictures
are built here.

## 0. Setup (once a session, ~2 min)
```sh
git clone --depth 1 https://github.com/lemomo-ai/lemo-opuscar.git ~/lemo-opuscar
cd ~/lemo-opuscar && sh plugin/skills/lemo-opuscar/scripts/setup.sh deps
```
Python is `~/lemo-opuscar/.venv/bin/python`. The narration is ours (SKILL.md step 4), never the library's voices.
The owner's own saved styles live on their Mac in `~/lemo-my-styles/` (its README lists them); stage them through
the device bridge when the chat is linked to the Mac.

## 1. Read before building
`AGENTS.md` (the workflow: a treatment first, never build inside `styles/`), the chosen `styles/<slug>/STYLE.md`
(its fixed look, colour, type, motion, camera, sound and pitfalls), `TECHNIQUE.md` and `core/README.md`. Only after
writing TREATMENT.md, read the style's `DEMO.md`/`demo/` to learn its engine; copy what you need into the film's own
folder; never reuse the demo's story.

## 2. Build
1. A film folder `~/films/<name>/` with TREATMENT.md: the acts, a colour line per act, the shot list on the voice's
   real timings (each line's start and end come from the takes in the voice folder; the cut follows the voice).
2. `index.html` + `film.js`/`scene.js` with the page contract: `window.render(t)` deterministic, `window.DUR`,
   `window.READY = true`, optional `window.EV = [{t, type, …}]` for sound cues and `window.TEXTS(t)` for the reading
   check.
3. 1080×1920, 24 fps. Library demos are 1920×1080: re-lay the composition for vertical (change hard-coded `W`/`H`),
   never crop.
4. Captions: the style's own type grammar, the chunk rules of `story-engine.md` §6, right to left for Arabic chunks.
   Arabic fonts: `npm i @fontsource/amiri` (classic, engraving and print styles), Reem Kufi (Art Deco), Baloo Bhaijaan 2
   (friendly); copy the `arabic-*-normal.woff2` files into the film's fonts, declare @font-face, draw with
   `ctx.direction = 'rtl'`. A missing font file (404) breaks `document.fonts.load` silently: check the paths.
5. Real photos of real watches are composited as images (never redrawn as a model). Transitions: the owner's rule
   (dissolves inside an act, a push into a new act, no whips).
6. Review stills every round with the Read tool, with zoom crops; at least two rounds before the video.

## 3. Sound
The narration (the voice takes in order, with their act pauses) and the brand's music (ducked under the voice, mixed
to −14 LUFS). Effects are **real recordings only** (`tools/find_sound.py`), at most 6 a minute, 16–20 dB under the
voice: the library's synthesised `sfx.py` and paper sounds are not used (the owner banned synthetic effects).

## 4. Commands
- Stills: `cd ~/lemo-opuscar && node core/render/still.mjs <dir> 0 5 9 --size 1080x1920`
- Contact sheet: `.venv/bin/python core/render/sheet.py out.jpg <imgs…> --cols 4 --w 480`
- Reading check: `node core/render/readcheck.mjs <dir> --size 1080x1920`
- Events: `node core/render/events.mjs <dir> --size 1080x1920`
- Video (in the background): `node core/render/video.mjs <dir> --size 1080x1920 --fps 24 --workers 3 --out <dir>/out/video.mp4`
- Mux (mux.sh often refuses our WAV): `ffmpeg -y -i video.mp4 -i mix.wav -map 0:v -map 1:a -c:v libx264 -crf 20
  -preset veryfast -pix_fmt yuv420p -af loudnorm=I=-14:TP=-1.2:LRA=11 -c:a aac -b:a 192k -shortest -movflags
  +faststart out.mp4`

## 5. Lessons
- Heavy scenes time out on load with many workers: build offscreen layers once, load the scene with
  `setTimeout(() => import('./scene.js'), 0)`, use at most 4 workers.
- WebGL runs in software here (slow): prefer 2D-canvas styles for quick tests.
- Kids' stories: Crayon Picture Book works well (a tall page with page turns, one printed line a page).
- Human figures built from coordinates are the hardest part; for character-heavy films offer the three-agent loop
  (builder, animator, art director; `wood-marquetry.md` §4) or the AI route.
- Saving a style the owner made: package it as `~/lemo-my-styles/<slug>/` (style.json, STYLE.md, CHANGES.md,
  DEMO.md, demo/ with build.sh, styleframe.jpg, test.mp4) plus a row in its README, and write it to the Mac only when
  they ask.

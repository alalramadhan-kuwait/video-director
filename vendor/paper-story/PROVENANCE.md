Copied read-only from audit/claude_success-story-video (.claude/skills/paper-story, video/brand/tk_endcard.py, public/icon-512.png) on 2026-10-14 for the studio. Changed here since (each in `git log` of the file):
- `scripts/render.mjs`: frames encoded in chunks of 900 and removed as each is done (`--chunk`); a fresh page every 1200 frames, a refused frame retried once, the frames removed however the
  render ends, a low-disk warning; `--safe zones.json` (words under a platform's buttons, `PM.safeZones`); `--textmap` (the words on screen and the frame
  without them, for the measured quality bar).
- `engine/stage.html`: loads `vendor/motion-kit` (the `kit` element) and, from `vendor/studio-ext` (ours), the safe-zone
  check, the text audit and the 3D watch movement (with `vendor/three` through an import map).
- `engine/paper.js`: the spoken caption word in `style.caption.active` (`activeLight` on a light tag); photos and
  cut-outs never boil (`noBoil` by type) and idle smoothly; the `breathe` idle.
- `engine/props-docu.js`: the map's `marker: "train"` (a drawn train on a railway line instead of the paper plane).
- `scripts/render.mjs` (2): music at -6 dB with a gentler duck (`audio.duck`), beds with a `lead` (J-cut) and a loopable
  `<name>_bed` take, the automatic paper place only for a banner that really comes in.
- `scripts/make-sfx.py`: train, train_bed, train_horn, gavel, tower_strike, footsteps, thud, tick_slow.
- `tk_endcard.py`: 3 s, no banner over the logo, no black scene after it.
- `engine/paper.js` (2): shot-size cameras (`camera.clamp`: the frame never shows the world's edge), the camera crossing
  the cut (`transition`: `through` push-through with `cutFocus`, `match`, `whip` right to left in an rtl film; the
  outgoing camera keeps its speed past the cut; `slide`/`push` follow the reading direction), directional motion blur
  on fast-moving elements and on whips (`motionBlur: false` / `noBlur` turn it off), and the asymmetric glide types
  `flyL`, `flyR`, `flyU`, `flyD`, `depth` (0.9 s in, 0.4 s out). `vendor/studio-ext/text-audit.js` skips a push-through
  while it settles.

- `scripts/render.mjs` (3), `engine/stage.html`, `engine/paper.js` (3): video clips (`vendor/studio-ext/clip.js`, ours: the
  `video` element). The renderer extracts each clip's frames once with ffmpeg (cached in `<storyboard>/.clip-frames/`)
  and awaits `PM.settle()` (every clip frame decoded) before each screenshot and each textmap frame; a clip never boils.

## Bang Motion (ideas and constants ported, no code or GSAP vendored)
The shot-size camera (`frameOn` with its edge clamp), the push-through constants, the whip with a directional blur and
the directional blur itself (`blurTween`: an SVG feGaussianBlur with separate x and y deviations, put on only while
the element moves) are re-implemented here from Bang Motion v1.19.0 (`references/techniques.md`, `assets/starter-*.html`):

    MIT License

    Copyright (c) 2026 Bang Tutorial

    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE.

GSAP is not under that licence and is not used.

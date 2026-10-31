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

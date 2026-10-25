Copied read-only from audit/claude_success-story-video (.claude/skills/paper-story, video/brand/tk_endcard.py, public/icon-512.png) on 2026-10-14 for the studio. Changed here since (each in `git log` of the file):
- `scripts/render.mjs`: a fresh page every 1200 frames, a refused frame retried once, the frames removed however the
  render ends, a low-disk warning; `--safe zones.json` (words under a platform's buttons, `PM.safeZones`); `--textmap` (the words on screen and the frame
  without them, for the measured quality bar).
- `engine/stage.html`: loads `vendor/motion-kit` (the `kit` element) and, from `vendor/studio-ext` (ours), the safe-zone
  check, the text audit and the 3D watch movement (with `vendor/three` through an import map).
- `engine/paper.js`: the spoken caption word in `style.caption.active` (`activeLight` on a light tag).

# Wood Marquetry: Time Keeper's own style

Patek Philippe-level cut-veneer art, everything drawn in code (canvas JS), rendered frame by frame with the
lemo-opuscar renderer (`code-styles.md` §0 and §4 for setup and commands). No image generation, no stock footage.

## 0. The style package
It lives on the owner's Mac at `~/lemo-my-styles/wood-marquetry/`: `STYLE.md` (all the rules), `LEARNINGS.md`
(figure, clothing, city and walk rules in numbers), `CHECKLIST.md` + `evalkit.py` (0–5 scoring, side by side, a 50 %
blend, foot-slide), `engine/wood.js` (the veneer engine), `engine/surfer.js` + `engine/walk.js` (a man with a board,
an 8-key walk solver), `engine/city/{pedestrian.js, walk.js, env.js}` (a city-casual man; a New York brownstone
street), `demo/`, `references/` (the reference art), `examples/` (approved videos).
- When the chat is linked to the Mac: stage the whole folder into the workspace and read STYLE.md and LEARNINGS.md
  fully before building.
- When it is not: ask once for the link or a zip; otherwise use the rules below and `../assets/wood.js`.
- Write back to the Mac only when the owner asks to save.

## 1. The fixed rules (never break)
- Every visible colour, shadow and shape is an individually cut veneer leaf with real-looking grain. Tone comes only
  from choosing a darker or lighter veneer.
- No digital gradients, blur, glow, cinematic light, brush strokes, cartoon or anime, 3D render, thick black outlines,
  or a wood filter over an image. A faint, even varnish sheen over the whole panel is allowed.
- Fine, Patek level: many **long thin leaves** (rows ~10–30 px tall, leaves 100–400 px long, joints offset), hairline
  seams ~0.7 px at ~30 %. A brick or mosaic look is a failure.
- **No border or frame line**: full bleed.
- **Open on the finished full-colour panel**: no pencil pattern, no leaf-by-leaf build, unless a making-of is asked.
- Motion is **rigid pieces only**: translate or rotate at joints; never stretch, morph or melt a leaf. Slow and simple.
- Shapes must be cuttable (no hairlines; thin railings ≥ ~14 px). The background simpler than the subject; not crowded.
- 1080×1920, 24 fps. Text, if any: cut lettering inlaid in the panel, not floating UI; the house style.
- In a Reel: the narration and the owner's sound rules from SKILL.md; a real watch appears as its real photo set into
  the panel like an inlaid plate, never redrawn in veneer as a real model.

## 2. Workflow
1. A short TREATMENT.md (subject, three structures, pick one), timed to the voice takes.
2. Background as offscreen layers built once (sky fixed, far layers slow, the ground at the walker's speed). `band()`
   for rows of leaves, `split`/`slabY` to cut shapes, `piece()` to lay each leaf.
3. Characters: start from `engine/city/pedestrian.js` or `engine/surfer.js`. From LEARNINGS.md: head ≈ 0.149 of the
   body height, ~7.5 heads tall; one continuous silhouette per limb with tonal leaves inside it (back dark, lit ridge
   light); no seam across a joint; real feet; hands with a thumb and 3–4 finger leaves; clothing as rigid pieces per
   bone; far limbs one veneer step darker; skin from the tone ladders. A new character is traced from a reference on
   a 25 px grid and **blend-checked at 50 % over the reference before shading**.
4. Walks: the 8-key cycle in walk.js with the stance solver: the planted foot pinned, heel → flat → heel-off → toe-off,
   ground speed = planted-foot speed (no foot slide), bob ~2.5 %, torso upright, arms opposite the legs (±~0.38 rad).
5. Review stills (and 2–3× zoom crops) every round against the references; at least three rounds.

## 3. Known fixes
- Heavy scenes: load with `setTimeout(() => import('./scene.js'), 0)`, at most 4 workers, grain texture size 512.
- Pages set `window.render(t)`, `window.DUR`, `window.READY = true`, optional `window.EV`.

## 4. Character-heavy jobs: the three-agent loop
Three background agents with separate folders: a builder (figure or environment), a motion animator, and an art
director who scores with CHECKLIST.md / evalkit.py each round and writes concrete, measurable fixes per owner. Relay
the critiques between them, integrate early (a composite finds scale problems first), stop when every category scores
≥ 4 or the gains flatten. Fold new rules into LEARNINGS.md and new modules into `engine/`; save to the Mac when the
owner agrees.

## 5. Honest limits
Backgrounds, architecture, motion and sound reach the owner's bar. Faces and hands built from coordinates plateau
around 3.5–4 / 5 against the reference art: say so, and offer a hybrid (AI character frames on the code background,
with the owner's yes to the credits) when they need more.

# The studio: the owner's dashboard (theme A)

https://claude.ai/artifact/UQ2iS18beg8zt9DztSLNZ6 — the owner follows every film here from the iPhone: its percentage,
the time left, and what waits for them (the owner, 2 Nov 2026: «i want to see % and timing to finishing and wait for
action if applicable»). Its look is the owner's pick, theme A, the celebration dial: cream ground, one bright colour
per film, rounded cards, a dark floating tab bar, little text.

The page's source is `studio-page/` in this repo (index.html, library.json); its media (film/, posters/, samples/,
carousel/, the old studio's panel/ avatars) are published files of the page only, never in git (the repo is public).
Several sessions publish it: before publishing, read the live page (Artifact `read`) and build on it, then copy the
result back into `studio-page/` in the same change. One version of the page holds at most 256 MB: drop superseded
drafts no record points to (`null` in `files`) before adding new media. Its records live in its database, never in
its source; write them with the ArtifactData tool (`url` above).

A carousel's working folder (spec.json, caption.txt, its cut-outs and cover; credited press photos included) is kept
on the page too, under `src/carousel/<id>/`, so any later session can change one slide and render it again; the
scratch folder of the session that made it does not outlive that session.

## Keep it current: at every step of SKILL.md
Write `films/<film id>` when a step starts, when it ends, and when a gate waits for the owner. Fields:

| field | what |
|---|---|
| `name`, `title` | the card's short name, the film's title |
| `order`, `color` | position on the list; one of #2BB5B8 #F2765F #E9A0C0 #A8D8A0 #F2C230 |
| `step` | 1–9, SKILL.md's steps: idea and research, hook and script, readers, voice, pace, style, pictures and build, review, delivery |
| `state` | `working` (Claude on it), `waiting` (a gate for the owner), `done` |
| `now` | while working: what is happening, in a few words («أسجّل الفصل الثاني») |
| `eta_min` | while working: minutes left, from what the step usually takes (voice ~1 min a section, stills ~3, full render ~8–12, critic round ~10) |
| `waiting` | while waiting: what the owner decides («موافقتك على السكربت») |
| `after_min` | while waiting: minutes to finish once they decide |
| `version`, `seconds`, `versions` | the latest version, its length, the version list newest first |
| `video`, `poster` | a published file of the page: a light copy of the film (720 px, crf ~29, under 15 MB) and its cover |
| `acts` | `[{name, time}]` once the voice exists |
| `meta` | type · language · look · voice |
| `done_text` | when done («جاهز للنشر», «منشور») |
| `kind` | `carousel` for a carousel (a Reel leaves it out) |
| `slides` | a carousel's PNGs in order, as published files (`carousel/<id>/01.png` …) |
| `caption` | the post caption; «شارك الكل» saves one zip of every slide and the caption (the Claude app allows one file per prompt, and its share sheet one file) and copies the caption; the numbers under it save one slide each |
| `of` | the record of the same topic in the other format (a carousel's Reel, a Reel's carousel): the page links the two, or offers «سوّ منه كاروسيل/ريل» |

The percentage is the share of steps done (step − 1 of 9; 100 when done). `studio/now` holds the line at the top:
`{busy, text, at}`.

## What the owner sends back
The film page's buttons (approve, change with a note) and the library's «ابدأ فلم بهالنوع» send a comment to Claude
when the platform allows it, and always add a document to `inbox` (`{film, kind, step, note, text, sent, at}`). On a
carousel the change box shows the slides to pick (one or more); the message names them («الغلاف، الشريحة 3») and the
inbox document carries their files in `slides`. On
«شيّك الاستوديو», or when a film waits, read `inbox` and act on what is new.

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
| `updated`, `changes` | **with every new version** (the owner: «شلون اعرف اذا هذي اخر نسخة تم تحديثها متى؟ وشنو كانت اخر التغيرات؟»): `updated` the time (ISO, UTC) and `changes` `[{v, at, what: [one short line per change, in the owner's words]}]`, newest first, at most 20. The film page shows «آخر تحديث» in Kuwait time with its age and the latest changes, the older ones folded; the cards show the version and its age. The studio's own text editor writes its entry itself |
| `video`, `poster` | a published file of the page: a light copy of the film (720 px, crf ~29, under 15 MB) and its cover |
| `final`, `caption` (a film) | **on the owner's approval, at once** (the owner: «مفروض بعد الموافقه يعطيني الفيديو جاهز للحفظ مع الكابشن»): the film at full size (1080×1920, two-pass to under 16 MB, a published file's limit) and its post caption (hook, the story in two lines, the reader's question, sources, credits, hashtags). An approved film shows «احفظ الفيلم ↗» (the share sheet's Save Video; the caption goes to the clipboard on the same tap) and its caption |
| `acts` | `[{name, time}]` once the voice exists |
| `meta` | type · language · look · voice |
| `done_text` | when done («جاهز للنشر», «منشور») |
| `kind` | `carousel` for a carousel (a Reel leaves it out) |
| `slides` | a carousel's PNGs in order, as published files (`carousel/<id>/01.png` …) |
| `caption` | the post caption; «شارك الكل» saves one zip of every slide and the caption (the Claude app allows one file per prompt, and its share sheet one file) and copies the caption; the numbers under it save one slide each |
| `of` | the record of the same topic in the other format (a carousel's Reel, a Reel's carousel): the page links the two, or offers «سوّ منه كاروسيل/ريل» |
| `spec`, `src` | a carousel's spec.json (its texts, layouts, pictures) and the published folder of its pictures (`src/carousel/<id>/`): with them the owner edits the text in the studio himself (below) |
| `history`, `edited` | the last 10 versions before an edit in the studio (`{version, spec, slides, caption, at}`; «رجّع النسخة السابقة» restores the newest), and `edited: studio` once the owner has changed it there |

The percentage is the share of steps done (step − 1 of 9; 100 when done). `studio/now` holds the line at the top:
`{busy, text, at}`.

## What the owner sends back
The film page's buttons (approve, change with a note) and the library's «ابدأ فلم بهالنوع» send a comment to Claude
when the platform allows it, and always add a document to `inbox` (`{film, kind, step, note, text, sent, at}`). On a
carousel the change box shows the slides to pick (one or more); the message names them («الغلاف، الشريحة 3») and the
inbox document carries their files in `slides`. On
«شيّك الاستوديو», or when a film waits, read `inbox` and act on what is new.

## The owner edits a carousel's text himself
The owner, 2 Nov 2026: «some time to edit or change the text on the carousel… shouldn't require a regeneration of the
whole picture». A carousel record with `spec` and `src` shows «✎ عدّل النص بنفسك»: the page draws each slide on the
phone with the kit's own layout (studio-page/index.html, `kitSlide`, a port of tools/carousel/carousel.mjs, the fonts
and the TK overlays published under `carousel-kit/`), with live checks (the cover's 73 characters, 12–32 words, a 2–4
word title, text running into the picture or off the slide, words outside the carousel's language, the reader's
question on the last slide). Saving uploads only the changed slides as assets (`/_blob/<id>` in `slides`), writes the
new `spec`, caption and version, keeps the old one in `history`, and leaves a note in `inbox`.
Each save also keeps **what the owner changed, word for word**: `changes[0].edits` (`[{where, field, key, before,
after}]`, the change log shows the changed words «before» ← «after») and the owner's optional «ليش غيّرته؟» (`why`),
copied into the inbox note. Log every one in `references/carousel-edits.md` with its lesson
(`tools/carousel/edits.py <record.json>` prints the entry) before the next carousel is written.
So when Claude next changes that carousel, **the record's `spec` is the truth**: write it to the working folder's
spec.json before rendering. A new carousel gets `spec` and `src` when it is first delivered (its folder published under
`src/carousel/<id>/`). Keep `carousel.mjs` and `kitSlide` in step: a layout change goes into both.

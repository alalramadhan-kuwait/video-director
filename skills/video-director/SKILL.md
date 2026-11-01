---
name: video-director
description: >-
  Make a short Arabic documentary video (Reels/TikTok/Instagram, 9:16) for Time Keeper or Diabetes History from an idea:
  research with sources, a story direction, an Arabic script with a chosen hook, free Arabic narration, real licensed
  photographs first (Wikimedia Commons), paper-story motion graphics in a chosen style, and one Instagram-ready film.
  It runs from idea to finished film on its own, using the brand config; the owner approves the finished film before
  anything is published. Nothing paid runs by itself. Use this whenever the user asks for
  a video, a Reel, an episode, «سوّ لي فيديو عن…», «فيديو عن ساعة…», a watch history, a brand story, or sends an idea
  for Time Keeper — even if they do not say "video director".
---

# مخرج الفيديو — making a film in the chat

The owner talks to you from an iPhone. Run the whole film yourself and ask for **one approval: the finished film,
before publishing**. Reply in Arabic (Kuwaiti is fine), short: **what is done, what remains, what you need from them.**
Never send long reports or ask for approval of intermediate steps. Stop and ask only for: paid generation, or a fact
you cannot source.

## Rules that never bend
- **No paid generation or spending without an explicit yes in this chat**: no ElevenLabs, no paid image or video
  models, no paid AI budget. Free tools only by default.
- **Real photos, always credited** (the owner relaxed the licence rule; rule 12j). First a free licence (Commons,
  `tools/find_photo.py`); when none shows the right thing well, a real photo from the maker, an auction house, a
  museum, a dealer or a watch site is fine, with its source on screen («via …») and its page recorded (`url:`,
  `page:`, `credit:`); the owner's own photos too. The build lists the credited ones so the owner sees them before
  publishing. Such photos are downloaded at build time and never committed to this public repository. Never a
  replica, homage or fake watch, never a generated or invented picture, never a photo passed off as something else.
- **Facts need sources.** Every claim in the script maps to a source; a popular but false claim is only said as a
  belief («يُقال…»), never as fact.
- **Never publish** without the owner's approval of the finished film. A requested change makes a new version; keep the old one.
- Label drafts honestly: the free voice is a draft voice, not the final narration.

## Brand
Fonts, captions, narration voice, watch-name pronunciation, music and logo come from one file:
`brand/timekeeper.json` (+ `brand/pronunciation.json`, `brand/music/`). Use it; do not restate them per film.
The music library is the whole Kevin MacLeod catalogue (1,443 tracks, CC BY 4.0, commercial use with credit),
filtered by the brand's mood; the owner's own licensed track in `brand/music/` wins if there is one.

## The owner's standards — read first, every film
**`references/storytelling.md`** holds the rules the owner set through their reviews: the story told in order and
connected, a sentence that leads into every change of scene, each scene showing only what is said in it, the reason
behind every change, the feelings named (sadness for every human moment), historical photos for historical events,
precise wording and no invented links, a world for every scene, a city zoom for every city, colour maps. Apply them all
without being asked; `tools/make_film.py` checks the checkable ones (`story:` must say «all rules kept»).

## The steps (all automatic; one approval at the end)
1. **Research** — trustworthy sources only (museum, archive, patent office, the brand only for its own claims,
   established references); each claim keeps its source link. Drop or soften what you cannot source. Find the causes
   (why each change happened), the human stories and their feelings, and the historical photographs.
2. **Hook + script** — pick the strongest honest hook yourself; written the way the Time Keeper news is written
   (`references/house-style.md`: news fusha in pause form, light, names in Arabic on screen and said in their own
   language), clear for listening, one idea per line, in chronological acts where each line leads into the next
   (`references/storytelling.md`).
   Then the reader panel (rule 6d, `references/reader-panel.md`): a novice, a medium and an expert reader, a
   filter, and their vote, before the owner sees it.
3. **Voice** — the owner's chosen voice: **Nasser AlJubaily** on ElevenLabs (voice cFUFIbKkO2iZFwS8cRnY, a Saudi
   «white dialect», warm storyteller; the owner, 1 Nov 2026: «عجبني ناصر», after «وايد واضح انه صوت الي»).
   eleven_multilingual_v2, seed 1234, stability .4, similarity .8, style .2, speaker boost, **speed 1.0 and no atempo**
   (speeding it up is what made the voice sound artificial), and each line sent with `previous_text`/`next_text` so the
   delivery flows across lines. A film that runs long is cut in the script (with the owner), never sped up. Silence
   trim only. Words from `brand/pronunciation.json` and the studio's pronunciation tab. (Abdullah, XdoLPWNt7ytn6BtU4FBf,
   made Halter 1 and 2.)
   OmniVoice (`arabic-narration` → `references/omnivoice.md`) stays the free fallback.
   **Anything audio the owner must hear (a voice test, a take, a music choice) is sent as an MP4** (a dark still
   with its name, the audio under it): the owner's chat does not play MP3 («I cant hear mp3 in this chat always make it mp4»). Listen-check the
   take yourself (Whisper for omissions/repetitions) and regenerate a passage that is wrong.
4. **Look** — the brand's default look (`paper-story`), or `look: data` in the film file (rule 18o: a dark stage,
   big numbers, one ruby/gold accent, as the owner chose for the rubies film); another only if the subject clearly calls for it
   (`motion-graphics`).
5. **Pictures** — real photos first: `python3 tools/find_photo.py "<what>" --save <dir>`, credited on screen;
   a drawing of a person when none is found; a watch is never drawn, only its real photo (rule 12h).
6. **Film** — write the film file `films/<name>.yaml` (example: `films/panerai.yaml`): each line's `text` (and `say`
   when the voice must read it differently, e.g. years as words), its `template` and `params` from
   `art/catalogue.yaml`, its `banner`, its world (`set`), its `mood`, and `event` / `change` + `because` where they
   apply; plus `photos` (Commons queries), `sources`, the `platform` and the written `hook`. Worlds (`director/studio/sets.py`,
   drawn in code, rule 18g): `underwater`, `sea_night`, `florence`, `workshop`, `radium`, `archive`, `auction_room` (a sale
   room, paddles rising, an empty frame for the lot's photo), `paris_rail` (dusk railway, a train crossing), `home_70s`
   and `home_70s_driver` (a 1970s kitchen; the second has a drawn `rail_driver` walking in), `paris_atelier` (a
   restorer's bench over the zinc roofs), `jura` (snow, fog, village lights), `basel_fair` (a 1998 fair hall),
   `swiss_atelier` (Halter's Sainte-Croix bench, the Jura through the window, drawn makers rising behind) and
   `waiting_years` (a tear-off calendar, 2003 to 2010, its pages falling). Then `python3 tools/make_film.py films/<name>.yaml <out>`:
   it voices, listens (Whisper), times the captions to the voice, draws, checks the story and the layout, adds the
   ducked music (its beats under the cuts) and the end card, keeps the size under the brand's limit, checks the words
   against the platform's buttons, makes the cover or the parts the platform needs and writes `credits.txt`. Fix every
   `story:` and `safe zones:` warning, look at every still in `<out>/scenes/` (text cut, overlaps, faint text, wrong photo), then render.
   **Sound on a line** (optional): `sfx: [{name: gavel, on: «كلمة»}, {name: train_horn, at: 2.5, gain: -8}]` plays an
   effect when the voice says that word (`nth: 2` for its second time, `offset: -0.2` to lead it) or at seconds from
   the cut; these cues are kept first when the film has more than 15 effects a minute. `bed: train` (or
   `{name, gain}`, a list, or `none`) replaces the scene's ambience. Sounds: the kit of `make-sfx.py`, including
   `train`, `train_horn`, `gavel`, `tower_strike`, `footsteps`, `thud`, `tick_slow`. **Real recordings first**
   where a sound carries the story: `python3 tools/find_sound.py gavel "gavel on wood"` (`--bed` for a loop under
   the voice) searches Openverse with no key or account, CC0 first then CC BY, never NC/ND/SA, and caches the WAV
   (trimmed, levelled to the kit) with its licence record outside git. In the film file
   `sounds: {gavel: "gavel on wood", train_bed: "steam train passing"}` plays the found sound wherever that name is
   used (`name: "found:<openverse id>"`, with `fallback: gavel`, pins one); every found sound the film plays goes in
   `credits.txt` (CC BY must be credited in the caption). Openverse often times out: the film then keeps the
   procedural sound and says so (`found sound:` lines), never fails. A `map` journey takes
   `marker: train` for a small drawn train instead of the paper plane. make_film levels the rest itself: beds 24–28 dB
   under the voice from 0.5 s before their cut, effects 3–6 dB under it, and every camera moving at least 3 %.
   Then the critic loop (`references/storytelling.md` rule 19c): `python3 tools/critic.py pack <out>`, a fresh agent
   reads the round folder and writes findings, fix the worst problems, render, `record`, repeat until «ship» (at most
   three rounds).
   **Send the finished film for approval**, with the sources, photo credits and the music credit line (it goes in the
   post caption).
   The owner approves or comments with time codes («عند 0:42 الخط صغير»); fix only that, resend.

## Setup in a fresh cloud session (once)
```bash
pip install numpy pyyaml gTTS faster-whisper imageio-ffmpeg     # ffmpeg, node and Chromium are usually there
python3 -m venv var/cutenv && var/cutenv/bin/pip install "rembg[cpu]"   # the paper cut-outs (export VD_CUTOUT_PYTHON=var/cutenv/bin/python)
python3 vendor/paper-story/scripts/make-sfx.py                  # the paper sound kit (made locally, free)
# optional: earshot ranks found sounds (MIT, CPU, ~1.1 GB of models), installed outside the repo, then
# export VD_EARSHOT=<venv>/bin/earshot   (github.com/Leonxlnx/earshot; pip install torch --index-url …/whl/cpu first)
npm i --prefix ~/.cache/paper-story playwright-core             # only if render.mjs says playwright-core is missing
```
A worked example of a whole short film (voice + scenes + render): `examples/explainer/build.py`
(`python3 examples/explainer/build.py <out-dir> stills` for frames, `... video` for the MP4).

## On the owner's own computer (optional)
The repository is also an app with phone screens for these approvals (`tools/setup_mac.sh`, then
`tools/run_mac.sh --lan`, opened from the iPhone with an access code). In a cloud chat the app's screens cannot be
reached from the phone, so the approvals happen in the chat as above.

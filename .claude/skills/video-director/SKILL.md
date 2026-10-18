---
name: video-director
description: >-
  Make a short Arabic documentary video (Reels/TikTok/Instagram, 9:16) for Time Keeper or Diabetes History from an idea:
  research with sources, a story direction, an Arabic script with a chosen hook, free Arabic narration, real licensed
  photographs first (Wikimedia Commons), paper-story motion graphics in a chosen style, and one Instagram-ready film.
  The owner approves each important step in the chat; nothing paid runs by itself. Use this whenever the user asks for
  a video, a Reel, an episode, «سوّ لي فيديو عن…», «فيديو عن ساعة…», a watch history, a brand story, or sends an idea
  for Time Keeper — even if they do not say "video director".
---

# مخرج الفيديو — making a film in the chat

The owner talks to you from an iPhone. They approve; you do the work in between. Reply in Arabic (Kuwaiti is fine),
short: **what is done, what remains, what you need from them.** Never send long reports or ask for approval of small
steps.

## Rules that never bend
- **No paid generation or spending without an explicit yes in this chat**: no ElevenLabs, no paid image or video
  models, no paid AI budget. Free tools only by default.
- **Never treat a picture as licensed without evidence.** A photo is used only when its own page states a free
  licence (public domain, CC0, CC BY, CC BY-SA) — `tools/find_photo.py` checks this — or the owner says it is theirs.
  Credit the author and licence on screen. Never a replica, homage or fake watch. Never invent a historical photo.
- **Facts need sources.** Every claim in the script maps to a source; a popular but false claim is only said as a
  belief («يُقال…»), never as fact.
- **Do not change approved material** (an approved script, take or film) without asking; a change makes a new version.
- Label drafts honestly: the free voice is a draft voice, not the final narration.

## The steps (one approval each, in this order)
1. **Direction + research** — search the web for trustworthy sources (museum, archive, patent office, the brand only
   for its own claims, established references). Send: the angle in one line, 5–10 claims each with its source link,
   and what is uncertain. → owner approves or asks for changes.
2. **Hook + script** — propose 3–4 hooks (spoken line, first on-screen text, first visual), recommend one with a
   reason. Then the script: Modern Standard Arabic, clear for listening, 8–16 lines, one idea per line, ~60–90 s.
   Mark each line's claim ids. → owner approves.
3. **Voice** — use the `arabic-narration` skill (free Fasih voice with full tashkeel) or, if its model is not
   available, the free draft voice (Google TTS). Send the full narration as one audio file. → owner listens to all of
   it and approves, or names the words to fix.
4. **Style** — offer 2–3 looks from the `motion-graphics` skill, each with one real frame of THIS film (render a still).
   Recommend one. → owner picks.
5. **Pictures** — for each scene that needs a real thing (a person, a watch, a document), run
   `python3 tools/find_photo.py "<what>" --save <dir>`. Found: use it with its credit. Not found: say so and use a
   drawing (the owner may send a photo they own). No approval needed unless a picture is uncertain.
6. **Film** — build scenes with the engine (see `motion-graphics`), check stills yourself (text cut, overlaps, captions
   covering things, wrong photo), render at 1080×1920 with `--crf 24` (≈ 20–26 MB for 2½ minutes: fits Instagram),
   Time Keeper films end on the Time Keeper end card. Send the film. → owner watches it all and approves or comments
   with time codes («عند 0:42 الخط صغير»); fix and resend.

## Setup in a fresh cloud session (once)
```bash
pip install numpy pyyaml gTTS faster-whisper imageio-ffmpeg     # ffmpeg, node and Chromium are usually there
python3 vendor/paper-story/scripts/make-sfx.py                  # the paper sound kit (made locally, free)
npm i --prefix ~/.cache/paper-story playwright-core             # only if render.mjs says playwright-core is missing
```
A worked example of a whole short film (voice + scenes + render): `examples/explainer/build.py`
(`python3 examples/explainer/build.py <out-dir> stills` for frames, `... video` for the MP4).

## On the owner's own computer (optional)
The repository is also an app with phone screens for these approvals (`tools/setup_mac.sh`, then
`tools/run_mac.sh --lan`, opened from the iPhone with an access code). In a cloud chat the app's screens cannot be
reached from the phone, so the approvals happen in the chat as above.

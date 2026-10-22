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
Never send long reports or ask for approval of intermediate steps. Stop and ask only for: paid generation, a picture
whose licence is uncertain, or a fact you cannot source.

## Rules that never bend
- **No paid generation or spending without an explicit yes in this chat**: no ElevenLabs, no paid image or video
  models, no paid AI budget. Free tools only by default.
- **Never treat a picture as licensed without evidence.** A photo is used only when its own page states a free
  licence (public domain, CC0, CC BY, CC BY-SA) — `tools/find_photo.py` checks this — or the owner says it is theirs.
  Credit the author and licence on screen. Never a replica, homage or fake watch. Never invent a historical photo.
- **Facts need sources.** Every claim in the script maps to a source; a popular but false claim is only said as a
  belief («يُقال…»), never as fact.
- **Never publish** without the owner's approval of the finished film. A requested change makes a new version; keep the old one.
- Label drafts honestly: the free voice is a draft voice, not the final narration.

## Brand
Fonts, captions, narration voice, watch-name pronunciation, music and logo come from one file:
`brand/timekeeper.json` (+ `brand/pronunciation.json`, `brand/music/`). Use it; do not restate them per film.

## The steps (all automatic; one approval at the end)
1. **Research** — trustworthy sources only (museum, archive, patent office, the brand only for its own claims,
   established references); each claim keeps its source link. Drop or soften what you cannot source.
2. **Hook + script** — pick the strongest honest hook yourself; Modern Standard Arabic, clear for listening,
   8–16 lines, one idea per line, ~60–90 s.
3. **Voice** — OmniVoice with the brand settings (`arabic-narration` → `references/omnivoice.md`, pass `--brand`):
   calm, natural documentary delivery, watch names from `brand/pronunciation.json`, natural speed. Listen-check the
   take yourself (Whisper for omissions/repetitions) and regenerate a passage that is wrong.
4. **Look** — the brand's default look (`paper-story`); another only if the subject clearly calls for it
   (`motion-graphics`).
5. **Pictures** — real photos first: `python3 tools/find_photo.py "<what>" --save <dir>`, credited on screen;
   a drawing when none is found.
6. **Film** — build scenes, check every still yourself (text cut, overlaps, captions covering things, wrong photo),
   render 1080×1920 with `--crf 24` (≈ 20–26 MB for 2½ minutes), brand music if the library has a licensed track,
   Time Keeper end card. **Send the finished film for approval**, with a one-line list of sources and photo credits.
   The owner approves or comments with time codes («عند 0:42 الخط صغير»); fix only that, resend.

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

---
name: reel-master
description: >-
  The one skill for making a Time Keeper Reel (or a Diabetes History episode), from an idea to the posted film:
  research with sources, the hook and the script in the house style, the reader panel's review, the voice (one take
  as one narration, tuned and paced), the transitions, choosing the style from the whole library (the paper-story engine
  looks, the 66 code-film styles, Wood Marquetry, an AI route), real credited photos, the build, the critic, and the
  cover, caption and credits for the post. Use it whenever the user sends an idea or asks for a video, a Reel, a
  script, a voice, a style, a cover or a post for a film: «سوّ لي فيديو عن…», «فيديو عن ساعة…», «اكتب سكربت»,
  «سجّل الصوت», «اختار ستايل», «غيّر الانتقالات», a watch history, a brand story, even if they name none of these
  steps. It replaces video-director, motion-graphics, arabic-narration, story-reel-script, code-film-styles,
  wood-marquetry-video and the Reel side of timekeeper-post.
---

# Reel Master: from an idea to the posted Reel

The owner writes from an iPhone, in Kuwaiti Arabic or English. Reply in their language, short: **what is done, what
remains, what you need from them.** Run every step yourself. The owner decides only at the gates marked **(owner)**:
the script with its hook (one question), the voice when it changes, the style, and the finished film. Nothing else
waits for them.

This skill joins seven earlier ones. Where they disagreed, **the owner's latest correction wins**; the table in
§ "Which rule wins" lists each conflict and its answer, so never fall back on an older skill's rule.

**The studio** (`references/studio.md`, https://claude.ai/artifact/UQ2iS18beg8zt9DztSLNZ6) shows the owner every film's
percentage, time left and what waits for them: update its film record at the start and end of every step and at every
gate, and read its inbox when a film waits.

## Rules that never bend
- **Facts need sources.** Every claim maps to a source; quote institutions in their own words. A popular myth is said
  only as a belief, or becomes the twist.
- **Real photos, credited.** Never a generated, replica or invented picture of a real watch, person or place; a watch
  is never drawn as a real model. A diagram of a principle is fine, **with no «رسم توضيحي مبسّط» label** (rule 18f).
- **No paid generation without an explicit yes in this chat** (paid image/video models, a new paid voice, credits).
  The voice the owner chose (step 4) is already approved.
- **Never publish** without the owner's approval of the finished film. A change makes a new version; keep the old one.
- **Audio the owner must hear goes as an MP4** (a still with the audio under it); their chat does not play MP3.
- **The repository is public**: no staff names, private chats or downloaded photos in it.
- Every correction the owner makes becomes a rule in `references/storytelling.md`, applied from the next film on.

## The flow (always in this order)

### 1. Idea → format, script type, language and research
**Format: a Reel, a carousel, or both** (the owner's choice; a Reel unless they ask). A carousel follows
`references/carousel.md` after the research and the script (the same facts, written as 4–5 slides) and skips the voice,
pace, style and film steps.
Pick the **script type** and the **language** from the script library (`brand/script_library.yaml`;
`python3 tools/script_library.py` lists them, `… <type> --language <lang>` shows a type's acts, skeleton lines and an
example). 14 types (hidden history, numbers explainer, biography, how it works, myth or fact, comparison, evolution,
top 5, record and auction, news and launch, parable → lesson, parable → brand, behind the scenes, question to the
viewer), each with its length, acts, hooks, languages and styles. Three languages, each with its rules and the same
lines written in it: **tk** (Time Keeper style, the default: the news' light fusha), **light** (light Arabic for every
Arab), **kuwaiti** (full Kuwaiti; the owner rejected it for Halter's voice, so two lines are voiced and sent as an MP4
before a full recording). The owner may name both with the idea; otherwise pick them and say so with the script.
The film file carries them: `script_type:` and `language:`; story_check holds the script to them and to the type's
length. The formats in `references/story-engine.md` §1 are the beats behind A/B/C. Then research: museums, archives, patent offices, established references; the brand only for its own claims. Keep
every source link. Find the causes (why each thing happened), the human stories and their feelings, the numbers, the
ironic final fact, and the real photographs (`python3 tools/find_photo.py "<what>" --save <dir>`). For a big topic,
split the research across parallel agents, one per angle, each saving notes with sources.

### 2. Hook and script
- **Hook:** follow the owner's guide `references/hooks.md` first (5 openings written, one picked, its checklist
  passed), then rule 6f, the type's `hooks` and `vendor/paper-story/references/hooks.md`; write the script from it; two alternatives go with the script so the
  owner can swap it at the script gate (one question, not two: the owner's choice, 2 Nov 2026). A physical first image
  or the owner's own question beats a teaser. The first frame shows the real subject, named.
- **Script:** in **acts** (3–5; `act: true` on the line that opens each), told in order after the hook, each line
  leading into the next (rule 3b): read it aloud as one paragraph; every line answers, continues or turns the one
  before. A date is not a bridge. One idea per line, 6–10 words.
- **House style** (`references/house-style.md`, rule 9e): the middle ground between fusha and Kuwaiti that the final
  news posts use; names written in Arabic on screen and said in their own language (`names:`); numbers on screen in
  English digits, said as words (`say:`); every abbreviation explained.
- **The close** (rule 6e): name the one fact the film leaves (`fact:`); the last lines return to the brand and the
  watch of the story, never ending on a lesson or a side story.
- **Length:** the type's range. `python3 tools/script_library.py --check films/<film>.yaml` gives the spoken length
  before any voice is paid for (`narration.chars_per_second`, about 10 for Jarnathan). Over budget: cut a fact,
  **never a bridge**, and never speed the voice up.
- Beats, writing rules and the shot direction for each format: `references/story-engine.md`.
- All the owner's standing rules for the story, the pictures, the look and the sound: `references/storytelling.md`
  (`tools/make_film.py` checks the checkable ones; `story:` must come back clean).

### 3. Review the script
The reader panel (`references/reader-panel.md`, rule 6d) before the owner sees it: **Noura** (knows nothing of watches,
simplifies every sentence), **Fahad** (medium), **Bu Khaled** (expert collector: facts, and «which watch? show it»),
**Salem** the filter (checks each concern against the research), and **Étienne** (brand, design and Reel specialist;
his brand «no» blocks). They read what the viewer gets: what is said, written and seen. At most three rounds. Then
send the script **(owner)** as a short numbered list by act, with its type and language, the chosen hook and two
alternatives, its estimated length, and a line on what the readers changed. The owner approves the script and the hook
together.

### 4. Voice
- **Every take goes to the owner on the pronunciation review page** (the owner, 3 Nov 2026: «always send me the
  artifact to check each word pronunciation»): since 7 Nov 2026 that page is **the studio's «الصوت والنطق» view**
  (`#filmvoice-<film id>` on the studio, fed by the record's `voice`, `references/studio.md`); send its link with the
  MP4. The older standalone page (https://claude.ai/artifact/U8RJAV2Qm8FdeBXkWdnEuT) and separate pick pages are
  retired, so his word choices live in one place. One view per take
  (the newest only), every line playable on its own, each word marked as Whisper heard it (missing / near), the
  rules checked, and the owner's marks saved; the link goes with the MP4 every time, and nothing is built on a take
  before the owner says it is done. The page is rebuilt from `heard.json` (Whisper word times) and the film file.
  **The owner edits the script on the page too** (6 Nov 2026: «خلني اقدر اعدل النص او اشيله او اضيف»): every line has
  «عدّل النص», «شيل الجملة» and «جملة بعدها», with «جملة بالبداية» at the top, saved with his word marks and sent in
  the same review. Apply the edits to the film file, re-record only the changed and added lines, cut the removed ones
  out of the take, and keep every line he did not touch as it was recorded.
- **The voice:** «Faisal», the owner's cloned Kuwaiti voice, ElevenLabs `ACGeXdn44RW29fHPITsl` (the owner, 2 Nov 2026:
  «I just added voice called faisal use it»), **on ElevenLabs v3 with emotion** (the owner chose it, «اعتمد ٢», over
  the older model, which read Faisal flat and in fusha): `python3 tools/record_flow.py films/<f>.yaml <dir> --voice
  ACGeXdn44RW29fHPITsl --model eleven_v3`, each line's `emotion:` («calm, curious», «proud», «sad, quietly»…) sent as an
  audio tag the voice performs and never says, the film's `voice.settings` (stability .5, speed .8) winning; the
  take is streamed, since a long v3 take outlasts the proxy. **The owner reviews the pronunciation** before pictures
  are made: a page per take (each line playable on its own, the words the transcription missed or heard differently
  highlighted, words to tap as wrong, notes) whose notes come back as a comment. **What his first review taught**
  (2 Nov 2026, 8 words): on v3, spelling «گ» by hand made it worse («تْگول، گطعت، يگنع، گيمتك» all marked): v3 says
  ق the Kuwaiti way by itself, so write the normal letter and keep گ/چ only where it was not marked («تگطع، جدام، چم،
  چذب، بوگت أگل، صدّگوها»); a formal verb gets the Kuwaiti one («يراقبون» → «يطالعون»); a vowel v3 reads the fusha
  way gets one light mark, never full tashkeel («سِباحة»، «نْحِسب»). His second review marked the last two («تگطع»,
  «بوگت»): **on v3 never write «گ» by hand.** **Pace** (the owner: «نخليها اسرع شوي»): speed .9, and since v3's own
  rhythm barely follows that setting while its held beats leave 0.7 s pauses, `python3 tools/tighten_take.py
  <voice_dir> --cap 0.5` cuts every silence over half a second to half a second, the voice untouched (127 → 110 s).
  His third review («أقل، القوارب، ثبت، كملتها»; «اسرع الى 0.9»): when v3 still reads a ق or ث word the fusha way, say
  it as a Kuwaiti would instead («بوقت أقل» → «أسرع منها»، «على القوارب» → «معاها بالبحر»، «ثبت» → «انحسب لها»), screen
  and voice alike; a doubled letter gets its shadda («كمّلتها»). The settled pace: speed 1.0 and `--cap 0.4`, as the
  reference reel (≈103 s for this script). **A watch name the voice clips** (the owner, 3 Nov 2026: «في خطا بكلام يقول
  ويستر اهو يقصد اويستر… واهي كلمة انجليزية»): v3 swallowed the bare «أويستر» into «ويستر», and the English
  «Oyster» came out «الايستر». Whisper (`tools/hear.py`) heard the right word in both of two takes only for
  «أُوْيِسْتَر», the first syllable fully voweled. On 4 Nov 2026 the owner heard six spellings in one sentence (same
  voice, settings and seed) and chose the plain English «Oyster» by ear, so it has no entry in
  `brand/pronunciation.json` and the voice reads it as written; on screen it stays in English letters (rule 9b). Whisper
  is a hint for names, never the judge: a name's spelling is settled by the owner's ear on the review page. Before v3: speed 0.7 (the owner: «I like faisal at 0.7 feels calm»):
  stability .75, style 0, the script's «…» kept as held beats. **Kuwaiti sounds in `say`** (the owner: «some… sound
  like they are not Kuwaiti fix it»): the voice reads letters as written, so spell the Kuwaiti sound where Kuwaitis
  say it, the screen keeping the normal spelling: ق → گ («گالت، تگول، تگطع، گبل، أگل، بوگت، صدّگوها، گيمتك، يگنع»), قدام →
  جدام, ك → چ («چم، چذب»), numbers in Kuwaiti words («ألف وتسعمية…، خمسطعش، سبعمية»). Before it, «Jarnathan - Confident and Versatile» `c6SfcYrb2t09NHXiT80T` (too hurried, below). A new
  voice is tried on two lines first and sent as an MP4 **(owner)**. Earlier voices and fallbacks: the owner's cloned
  «Ali TK» `WBd6y9HGGbIZZafgVlGr`, Nasser `cFUFIbKkO2iZFwS8cRnY`, Abdullah `XdoLPWNt7ytn6BtU4FBf`; free: OmniVoice or
  Fasih (`skills/arabic-narration/GUIDE.md`, the full Arabic pronunciation system).
- **Calm, and Kuwaiti or plain Arabic, never Levantine** (the owner, 2 Nov 2026, on the Gleitze film: «this one feels
  he is like in a hurry… the other voice feel more calm», then of the calm ones: «مشكلة فيهم لهجة شامية. وانا احتاج
  لهجة كويتي او عربية مبسطة بدون لهجة»). Jarnathan is an English «confident, conversational» voice: in Arabic it
  talks about 15% faster than the reference storyteller and then stops long (stop-start). Pick a storytelling voice
  with a Kuwaiti or Gulf accent (ElevenLabs library: Hasan, Mustafa Abdulla, Mohamed, Ahmed, Mohammed, AbuTaha), or
  a plain-fusha script read by a calm voice; a library voice tagged «modern standard» can still sound Levantine.
  Compare candidates on the same opening (`voice-compare.mp4`, one labelled segment each) and let the owner choose.
- **One narrator, one story, one take** (the owner, 2 Nov 2026: «The narrator is telling one continuous story, not
  performing each scene independently. His emotions should develop naturally with the story, not restart with every
  scene»). The order of work is the owner's: **the full script → one voice take → the timings of its sentences and
  words → the scenes by meaning → the scenes laid on the audio.** The voice is the base; the pictures follow it.
  1. *Read the whole story first* and give lines a `tone:` (calm, serious, warm, curious, surprised, excited; a line
     without one carries the tone before it). `director/narration.py` checks the arc: open curious, never a jump of
     more than one step between neighbours (nor a reset at a new act), surprise or excitement on two lines at most,
     where the information deserves it.
  2. *Record it whole:* `python3 tools/record_flow.py films/<film>.yaml <voice_dir> --voice <id> --name "<name>"`
     reads the entire script in one pass (one personality, energy and pace that develop with the story), stops first
     if the arc breaks, and cuts the take into one piece per line in the middle of the silences on ElevenLabs' own
     timings. Only a script over 4,500 characters is read act by act, with the acts around it as context and the same
     settings. eleven_multilingual_v2, seed 1234, stability .5, similarity .8, style .15, speaker boost, **speed 1.0,
     no atempo**. Delivery is written into the text itself: «…» for a held beat, «؟» for a real question, commas for
     breath; no stacked exclamations, no exaggerated excitement.
  3. *The scenes follow the audio:* the pieces carry `continuous` in their records, so make_film keeps their pauses
     (no trimming, no added gaps: `gap:` applies only to line-by-line takes) and lays the scenes end to end on them;
     the narration in the film is the take exactly as it was read. One tone decision for the whole narration (a
     boomy voice is evened out on every line or on none).
  4. *Listen without the pictures:* `python3 tools/hear_flow.py films/<film>.yaml <voice_dir>` prints the arc, names
     any join where loudness (>3 dB), pitch (>12%) or pace (>25%) jumps as if a new recording had started, and writes
     `<voice_dir>/narration.mp4` to listen to on the phone. A narration that sounds stitched is re-recorded before
     anything is built.
- **Check:** `python3 tools/hear.py <voice_dir>/*.wav` (Whisper): every word there, nothing added (a
  cloned voice once added «مرحبا»). Whisper misspells Arabic; it judges missing or extra words, not pronunciation.
  Fix a mispronounced word in `brand/pronunciation.json`, then re-record that act.

### 5. Tune: pace, pauses, transitions, sound
- **Pace:** `gap: {tail: 0.1, pause: 0}` in the film file; the takes' own breaths join the lines. The last line of an
  act gets `pause: 0.35`; the pause before the twist is the longest in the film (up to 1 s). Never speed up.
- **Transitions** (rule 18e): in a film told in acts, scenes inside an act dissolve (`match` when two pictures line up,
  else `fade`, the camera still moving); only a new act is pushed into (`through`). No whips. A line can still ask
  (`cut: push|match|fade|cut|whip`).
- **Camera:** each scene changes shot size on the words that carry it; a still frame never holds. A whole drawing or
  two prints side by side get `shots: [{at: 0, to: wide}]` (add `focus: [x, y]` to centre them).
- **Sound** (rules 18m, 18n): music from the brand library (Kevin MacLeod, CC BY 4.0, credited), ducked under the voice,
  its beats under the cuts. **Only real recorded effects** (`tools/find_sound.py`, CC0/CC BY), at most 6 a minute,
  16–20 dB under the voice, felt more than heard; never a synthetic whoosh. One signature sound for the hook and the
  close (a tick, a crown click) is enough.
- **The watermark** (storytelling 18r): every film carries the tk monogram top left, off for the end card;
  make_film adds it, an AI-route film runs `tools/tk_watermark.py` before its final encode.
- **On screen:** the captions plus **one** block of text at a time; no AI caption (an AI drawing is credited only in
  the credits).

### 6. Choose the style from the library (owner)
Read the story (faces and acting? a mechanism or object? numbers? a period? luxury?) and recommend **three** styles
from `references/style-library.md`, best first, each with why it fits, its trade-off, the tool and its cost; ask once
with AskUserQuestion. Show a real still of this film in the engine looks when you can. The library:
- **Engine looks** (free, `tools/make_film.py`): `paper` (the brand default), `data` (dark stage, big numbers, one
  ruby/gold accent: the rubies film), technical drawing, dark keynote, archival collage; 30+ scene templates
  (`art/catalogue.yaml`), worlds, city zooms, real-movement photos with ringed jewels (`jewel_photo`).
- **The 66 code-film styles** (lemo-opuscar, free): newsreel, copperplate engraving, Art Deco, blueprint, exploded
  teardown, ukiyo-e… (`references/code-styles.md`).
- **Wood Marquetry**, Time Keeper's own signature style (`references/wood-marquetry.md`).
- **AI route** (Higgsfield, credits, explicit yes): clay 3D, stylized 3D, cinematic, for character-heavy parables.

### 7. Pictures and build
- **Engine route:** write `films/<name>.yaml` (example: `films/panerai.yaml`): per line `text`, `say`, `template`,
  `params`, `banner`, `set`, `mood`, `act`, `shots`, `cut`, `sfx`; plus `photos` (with `credit`, `page`, `licence`),
  `sources`, `names`, `look`, `gap`. Then `python3 tools/make_film.py films/<name>.yaml <out> --voice-dir <voice_dir>`
  (`--stills-only` first). Fix every `story:` and `safe zones:` warning; look at every still in `<out>/scenes/`
  (text cut, overlaps, a cropped drawing, the wrong photo, a missing photo panel). Then the full render (in the
  background). Photos and private files live in `films/private/` (never in git).
- **Code route:** hand the timeline (each line's start and end from the voice takes, its caption chunks, its sound
  cues) to the chosen style's build (`references/code-styles.md` or `references/wood-marquetry.md`), mux with the
  narration and the ducked music.
- **AI route:** per-shot prompts (`references/story-engine.md` §7), confirm the credits first, assemble on the voice
  timeline. Faces that feel, close shots and one palette per act (rule 18p); the music about 5 dB under the voice
  (`references/ai-film.md`).

### 8. Review the film
- A contact sheet of the film (one frame every ~4.5 s) and the stills of every scene: look at each.
- **The critic loop** (rule 19c): `python3 tools/critic.py pack <out>`; a fresh critic and Étienne review the round;
  fix the worst; at most three rounds.
- **The sound check** (earshot, github.com/Leonxlnx/earshot, MIT, CPU only; the owner tried it on the Gleitze film,
  3 Nov 2026: «جربه على فيلم السباحة»): on the finished MP4, `earshot measure <film> --light` must show 0 clipped
  samples and a true peak at or under -1 dBTP; `earshot sheet <film> --detail normal` draws the frames, spectrogram,
  loudness and cut sync (look at it); `earshot realness <effect.wav>` on every sound effect, since only real
  recordings are allowed (rule 18m). Export the sound in stereo (two identical channels): on a mono file two
  meters disagreed by 3 dB (-12.5 against -15.5 LUFS); in stereo both read -16.0. Gleitze v5's first final had
  18 clipped samples (true peak +0.1 dBTP) after its AAC encodes: a limiter at 0.79 (`alimiter=limit=0.79:level=false`)
  and stereo fixed it (-4.8 dBTP). It also showed the end card's ticks are code-synthesized (p_real 0.01).
  Install once, outside the repo: `git clone https://github.com/Leonxlnx/earshot`, then `python3.11 -m venv .venv`,
  `.venv/bin/pip install torch --index-url https://download.pytorch.org/whl/cpu`, `.venv/bin/pip install -e .`;
  its models (about 1.1 GB) download on first use. Never its `llm` command (it uploads audio). It does not judge
  speech, pronunciation or taste: Whisper, the critic and the owner do.
- **The expert check:** anything a collector would catch (which jewels are ringed, which watch is shown, a date) goes
  to Bu Khaled with the frames before the owner sees it.

### 9. Deliver (owner)
Send the MP4 (with a one-line caption saying what changed), then the credits (`<out>/credits.txt`, cleaned: no local
paths, licences named), the sources, and the post caption in the house style with the music credit. For the post:
the cover (`<out>/cover.png`) and, if wanted, a carousel in the Time Keeper template (`references/post.md`). The owner
approves or comments with time codes; fix only that and resend. Never post without their yes.

### 10. After posting: read the numbers (owner)
The owner presses «تم النشر ✓» in the studio. Its numbers are read at 48 hours and at 7 days, straight from
Instagram through Supabase (`studio/ig`; screenshots only when the sync is down), judged against our own earlier posts, and turned into lessons and the algorithm recipe
(`references/insights.md`). Étienne's daily brief adds algorithm tips and reminds him when a read is due.

## Which rule wins (the older skills disagreed)
| Topic | Older rule | The owner's rule now |
|---|---|---|
| Language | «Kuwaiti dialect, not MSA» (story-reel-script) | the house style: between fusha and Kuwaiti, from the final news posts (rule 9e) |
| Voice | OmniVoice, or one file per line | one take of the whole script (`tools/record_flow.py`), the scenes laid on it, checked by `tools/hear_flow.py`; Jarnathan on ElevenLabs; OmniVoice/Fasih are the free fallback |
| Speed | `speed` to fit a shot | never sped up; cut the script |
| Transitions | «no generic dissolves», whips on movement | dissolves inside an act, a push into a new act, no whips (rule 3b, 18e) |
| Sound effects | synthesised kit (`pluck.py`, `sfx.py`, paper sounds) | real recordings only, ≤ 6 a minute, 16–20 dB under the voice |
| Text on screen | captions, titles, cards, labels | captions plus one block of text; no «simplified drawing» label; no AI caption |
| Captions | yellow Clayrified captions | the brand's captions (gold active word; flat dark chips in the data look), 2–5-word chunks |
| Approvals | one approval at the end (video-director) / don't ask before the script (story-reel-script) | the gates above: script with its hook, voice change, style, film |
| Comparing watches | two dial photos side by side | real movements with their visible jewels ringed, checked by an expert |
| Numbers on screen | Arabic-Indic or English | English digits |

## Setup in a fresh cloud session (once)
```bash
git clone https://github.com/alalramadhan-kuwait/video-director && cd video-director   # if the session lacks it
pip install numpy pyyaml gTTS faster-whisper imageio-ffmpeg
python3 vendor/paper-story/scripts/make-sfx.py
python3 -m venv var/cutenv && var/cutenv/bin/pip install "rembg[cpu]"   # paper cut-outs (VD_CUTOUT_PYTHON)
./run_tests.sh                                                             # before any pull request
```
The ElevenLabs key comes from the environment or the session's proxy; never write it anywhere. Merge your own pull
requests once the tests pass.

## Files
- `references/storytelling.md`: every rule the owner set (the story, facts, pictures, look and sound, delivery).
- `brand/script_library.yaml` (+ `tools/script_library.py`): the script types and the three languages with rules and examples.
- `references/house-style.md`: how Time Keeper writes, from 1,792 final news posts.
- `references/reader-panel.md`: the readers, the filter, the vote, Étienne.
- `references/story-engine.md`: formats A/B/C, beats, writing rules, delivery marks, shot direction, AI prompts.
- `references/style-library.md`: every style and template, fit rules, how to present three.
- `references/code-styles.md`: building in one of the 66 lemo-opuscar styles.
- `references/wood-marquetry.md` + `assets/wood.js`: the Wood Marquetry rules and veneer engine.
- `references/post.md`: the cover, the carousel template, the caption and the credits.
- `references/studio.md`: the owner's dashboard, its records and how to keep it current.
- `references/carousel.md` + `tools/carousel/`: the topic as a TK carousel, with its caption, saved from the studio.
- `references/insights.md`: after posting: the 48 h and 7 day reads, the verdict against our own posts, the recipe.
- `references/reference-reels.md`: every reference Reel the owner sent, measured, and what we take from each (the "how it works" series format).
- `skills/arabic-narration/GUIDE.md`: the free Arabic voice engines and the pronunciation review page.

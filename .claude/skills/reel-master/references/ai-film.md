# The AI-video film: a Clayrified-grade Reel in our paper-cut look

The owner, 2 Nov 2026, sending a @clayrified_ reel (the spit on the Buddha, 77 s): «is it able to produce something
similar… instead of the clay… the paper cut style that we are using… Higgsfield… Seedance 2.5… notice the tone of
the speaking, the zooms, the camera movement, all of this I need to be recorded and able to achieve the same quality».
This file records that reel, measured (`tools/reel_measure.py`), and the route that reaches it. Copy its engine, never
its story or its clay identity (story-engine.md).

## The benchmark, measured
| | The reel | Our rule today |
|---|---|---|
| Length | 77 s, 28 sentences, 282 English words | 60–90 s |
| Shots | **43, 33.5 a minute**; 1.8 s on average (0.7–3.4 s) | 35–45 a minute (story-engine §5) |
| Longest shots | the sleepless night (3.4 s), the turn to «you» (3.3 s), the callback (2.5 s) | the twist held 2.5–3.5 s |
| Cuts | hard cuts on phrase ends, one caption chunk ≈ one shot; one milky dissolve into a memory (54 s) | dissolves inside an act, no whips (3b, 18e) |
| Voice pace | 3.7 words/s, 19–28 characters/s, steady | never sped up |
| Pauses | 26 short ones (~0.3 s); **the longest is 0.42 s**: no long silence, even before the twist | `///` 1–1.5 s before the twist |
| Loudness | every sentence within −14.4 to −18.4 dB: one take, one distance from the mic | one take (rule 4) |
| Pitch | story ~130–170 Hz; the calm character's lines lower and quieter («I cannot forgive you»); the lesson rises to 170–215 Hz, warmer, speaking to «you» | ENERGY arc in director/narration.py |
| Under the voice | a bed only ~5 dB below the speech between words (music and room tone, never silence) | the same, ~5 dB, in an AI film (the owner, 3 Nov 2026) |
| Captions | 2–3 words, yellow bold serif with a dark edge, centred just under the middle, no highlighted word | the brand's gold active word |

**The voice:** a close, warm male storyteller, unhurried but never slow. Present tense, short sentences, no
theatrics. Emotion comes from pace and pitch, not volume. The quoted lines are said softly. The lesson lifts a little
and turns to the listener. One take, no gaps of silence. In Kuwaiti: Jarnathan or Abdullah, one take, `calm → serious →
warm` (narration.py), punctuation for the beats.

**The camera:** almost always locked or a slow push-in (about 5–10% over a shot). The motion is the acting inside
the frame, not the camera. Seen in the reel:
- extreme close-ups and macro inserts: the drop running down a cheek, a hand on a coin purse over a bowl, a lamp
  flame going out, footprints in sand blowing away;
- an over-the-shoulder two-shot for every exchange, cut action → reaction (0.7–1 s reactions);
- a wide establishing shot when the place changes (the tree, the bedroom), then straight back to close-ups;
- a push into the dream (a blue, ghostly face over the bed);
- emotion as an in-shot change of the character: a face turning red with anger, grey when pale, a tear forming.

**Light and colour by act:** warm day for the story; deep blue night with one warm lamp for the guilt; day again for
the twist; golden-hour garden for the lesson; a milky, faded dissolve for memories.

**The lesson section** has a new modern cast in the same look, in three escalating everyday scenes (others → you).
It ends on a gesture that rhymes with the story («stop wiping your face» ↔ the wiped cheek).

**Picture detail:** handmade texture, real depth of field (soft background, sharp subject), large expressive eyes, a
small set lit like a miniature. Every shot reads in a second.

## The route, in paper cut
1. **Script and voice first**, as every film (SKILL.md 1–4): one take, the scenes follow the audio. Split the
   lines at the caption chunks so that **each line is one shot** (about 40 lines for 75 s). A line carries one
   `clip:` (director/studio/clips.py), so the shot count is the line count. A clip may serve several lines:
   `clip: {file: s3.mp4, from: 4.2}` starts that line 4.2 s into it, so one multi-shot generation (a scene of
   3–5 shots, 10–15 s, with its own cuts) covers a run of lines and nothing generated is thrown away.
2. **A paper-cut character and set bible:** each character drawn as a paper cut-out (layered card, visible cut edges,
   paper grain, a soft drop shadow between layers), front, three-quarter and profile, plus the sets. Make them as
   stills (Nano Banana 2, about 1.5–2 credits each), the owner approves them before any video.
3. **The shots:** Seedance 2.5 on Higgsfield, `omni_reference` with the bible images as `image_references`, 9:16,
   `generate_audio: false`, one English prompt per shot as story-engine §7 says (a style-lock sentence first:
   «handmade paper-cut stop-motion, layered card, visible paper edges and grain, miniature set, shallow depth of
   field»), then the size and angle, the action, the light, the camera move (a slow push-in, or locked). Use the
   reel's shot vocabulary above. A watch is a real photo over a clip (`mode: behind`) **unless the owner asks for it
   drawn** (3 Nov 2026, the Gleitze film: «خل مشاهد الساعة مرسومة لساعتهم وتكون الساعة واضحة واهي تسبح ولابستها»):
   then it is the story's own model, faithful to a period source (the Oyster from the Daily Mail advert of 24 Nov
   1927): first one paper-cut still of the watch from that source (Nano Banana, «keep its shape and dial faithful, no
   brand name, no readable text»), then every watch scene takes that still as an `image_reference`, the watch clearly
   visible (on her, in the box, under the water, under the lamp, at the auction). The real advert stays as the proof.
4. **Draft, then final:** `draft: true` (480p) for every shot, the owner approves the cut, then the kept drafts are
   finalised (`draft_job_id`, 1080p). A shot that drifts from the paper look (clay, plastic 3D) is redone.
5. **Assemble** with make_film: clips on their lines, the one-take voice, the bed under it, captions, credits
   («فيديو بالذكاء الاصطناعي (Seedance 2.5 · Higgsfield)»).

**Cost (always confirmed with the owner first):** Seedance 2.5 has been about 35 credits a 5 s clip on this account
(Nov 2026), about 7 a second. One 5 s clip per 1.8 s shot wastes two thirds of it: 40 clips ≈ 1,400 credits. With
multi-shot scenes (`from`) the footage is about the film's length: 75–90 s ≈ 550–650 credits, about 800 with
retakes. Drafts come first; ask Higgsfield the draft and final prices before starting. First a test of 2–3 scenes
(about 100 credits) to see that Seedance holds the paper look and the characters across cuts. The voice is
ElevenLabs, as for any film.

## The owner's choice: follow the reel
The owner, 2 Nov 2026: «Follow this one. It is really doing good.» For an AI-video film (this route) the reel wins
over our older rules:
- **Hard cuts on phrase ends**, one caption chunk ≈ one shot; a dissolve only into a memory or a dream. (Rules 3b and
  18e, dissolves inside an act, stay for the engine looks.)
- **No silence over about 0.4 s**, the twist included: the beat comes from a short sentence and a held shot, not a
  gap. The bed under the voice never stops.
- **Captions as the reel's:** 2–3 words, bold yellow serif with a dark edge, centred just under the middle, no
  highlighted word.
- Everything measured above is the target: 33–40 shots a minute, a still or slowly pushing camera, the acting and
  the in-shot changes carrying the emotion, light by act, one warm close take.

## The owner's notes on the first film (Gleitze, 3 Nov 2026)
The first film on this route («السباحة اللي باعت ساعة», 103 s), measured beside the reel with `tools/reel_measure.py`:
27.9 shots a minute (the reel 33.5), 2.1 s a shot, the longest pause 0.54 s, the music 17 dB under the voice (the reel
4.9). The owner's answers became these rules for every AI film:
- **The music as the reel's** («نعدل الموسيقى ونوصلها لنفس الريل»): about 5 dB under the voice between words,
  measured, not guessed. On Gleitze the Bittersweet bed went from `volume=-21dB` with a hard duck
  (`sidechaincompress` threshold 0.03, ratio 4) to `volume=-5dB` with a light one (threshold 0.1, ratio 2) and a
  limiter at the end: 4.7 dB under, the voice still at -16 LUFS. Measure the mix the way reel_measure does (the median
  loudness of the words against the median of the gaps over 0.3 s) and set the bed until the gap is 4–6 dB. This
  replaces «felt, not heard» (storytelling 18i) for this route only.
- **Faces that feel, close shots, light by act** (storytelling 18p): the reel's biggest lead over Gleitze. Write the
  per-act palette and the close-up/reaction list into the shot plan before the prompts, and prompt every face for
  its feeling («her eyes wide, her face draining pale»).
- **The length follows the story** («الطول زين لانه قصتنا فيها تفاصيل اكثر»): a story with more facts may run past
  the reel's 77 s (Gleitze 103 s); never cut a fact or a bridge only to reach it. The pace inside it (shots a minute,
  no silence over 0.4 s) still follows the reel.
- **The close returns to the brand and fixes the fact** (storytelling 6e).
- **A flat page is a paper object in the world**: an archive picture (the 1927 ad) sits on a desk or in a hand as a
  paper-cut newspaper the camera pushes into, not as two flat cards in a row.


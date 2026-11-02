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
| Under the voice | a bed only ~5 dB below the speech between words (music and room tone, never silence) | felt, not heard |
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
   reel's shot vocabulary above. A watch is never generated: a real photo over a clip (`mode: behind`).
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

## Open with the owner
- **Cuts:** the reel cuts hard on phrases, our rule says dissolves inside an act. Which?
- **Pauses:** the reel never stops for more than 0.4 s, our rule allows a 1–1.5 s silence before the twist.
- **Captions:** their yellow serif, or ours.

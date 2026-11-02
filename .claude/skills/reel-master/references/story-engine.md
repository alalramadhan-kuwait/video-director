# The story engine: formats, beats, writing, direction

From six analysed @clayrified_ reels (cookie thief, two monks, the king's chalk line, spit on the Buddha, Bernays's
bacon, a message in a bottle) and Time Keeper's own films (10:10 in Art Deco, the bottle reel side by side with the
original, «ليش داخل ساعتك ياقوت؟» in Copperplate Engraving and then in the data look). Copy the storytelling and
directing engine, never their stories or their visual identity.

Where this file and `storytelling.md` disagree, `storytelling.md` wins: it holds the owner's own corrections (the
table «Which rule wins» in SKILL.md lists them).

## 1. Pick the format
- **A) Parable → life lesson.** A value (patience, timing, legacy, envy, presence); the watch is the story's central
  object and becomes the metaphor.
- **B) Hidden true history.** A real event behind something everyone takes for granted (10:10 in adverts, the quartz
  crisis, jewel bearings, how a model became an icon, why a complication exists). The final ironic fact is the moral;
  no «in life» section. A closing question to the viewer («وساعتك… شكم حبة فيها؟») is fine when the owner wants
  comments; keep the ironic fact just before it. Most Time Keeper films are B.
- **C) Parable → brand.** A short parable whose lesson becomes the reason to follow or buy. Brand proof uses only true
  facts the owner stated or that are verified (Time Keeper since 2018, about a quarter-million followers). Never
  invent numbers, views or results.

If the owner gives only a topic, pick the format yourself. If they give a finished script, keep their content and
structure: fact-check it, split long lines, fix the hook if needed, and say in one line what changed.

## 2. Beats
### A (65–78 s, about 65 % story and 35 % lesson)
| Time | Beat | Rule |
|---|---|---|
| 0–5 s | Hook | A vivid physical image, present tense, mid-action. The problem is visible in the first sentence. |
| 5–22 s | Silent action | Characters act more than talk. Short sentences. |
| 22–35 s | Rule of three | Three parallel beats that build pressure. |
| ~34 s | Emotional peak | An inner thought or an outburst: the only dialogue in the film. |
| 40–50 s | Twist | One short line from a calm character: a paradox or a question. The longest pause comes right before it. |
| ~50 s | Turn to the viewer | «تدري؟ بالحياة…» / «وايد مرات بالدنيا…» |
| 50–70 s | Three modern examples | Hyper-specific everyday details, escalating: others → you → «right now». |
| last 3 s | Callback | An imperative that reuses the story's object or verb (for watches: wind it, set it, look at the dial). |

### B (60–90 s)
| Time | Beat | Rule |
|---|---|---|
| 0–9 s | Normal + flip | An everyday image everyone accepts, then the flip question. A physical first image beats a bare question; the owner's own question is best of all («شنو الفرق بين ساعة فيها 17 حبة ياقوت… وساعة فيها 21؟»). |
| 9–25 s | Credibility | Real names, the year, the place, one surprising credential. |
| 25–60 s | Mechanism | Step by step; each step a small reversal. Negation beats; numbers as punches, escalating. |
| 60–72 s | Payoff | Restate the absurd result in one line; come back to the hook's question («نرجع لسؤالنا…»). |
| last 3 s | Ironic final fact or question | One true fact that reframes everything, or the question to the viewer. |

### C (55–60 s)
| Time | Beat | Rule |
|---|---|---|
| 0–10 s | Hook + rule of three | The hero tries the obvious way three times; it fails each time. |
| 10–18 s | Insight | The hero stops, observes, finds the hidden mechanism; it works. |
| 18–23 s | Proof | A reply comes back; hold with near silence. |
| 23–25 s | Bridge | «اليوم… البحر هو تلفونك.» |
| 25–41 s | Brand journey | «We used to be that man» → years of trying → one true milestone. |
| 41–51 s | Second half | «But [mechanism] is only half…» + three concrete things the brand gives. |
| last 6 s | Callback + CTA | A negative and a positive command reusing the story's verbs, then follow. |

Every format can end with the follow line after the last line: «تابعنا… لا تفوتك الحكاية الياية.»

**The acts are the beats.** Mark the line that opens each beat group with `act: true`; the voice is read as one take
of the whole script, its tone developing across the acts, and the cuts follow the acts (SKILL.md steps 4–5).

## 3. Writing
- One line ≈ 2–3 s: 6–10 Arabic words. Split a longer line in two; one idea per line.
- Short lines slow the film down; never two long sentences in a row near the twist.
- Verbs carry it; no piled-up adjectives. Don't explain the moral twice; don't add a second one.
- **Every line hands on to the next** (rule 3b): «وقبل الجواب…», «لأن…», «والحل جاء من…», «لكنهم طمعوا…»,
  «ونجحوا…», «ولما رخص…», «نرجع لسؤالنا…». A line that opens only on a date is not led into.
- The language is the house style (`house-style.md`), not pure dialect and not stiff fusha.
- Captions with Latin words or handles: never end an Arabic caption with a Latin word or an @handle followed by
  punctuation (the text direction flips); rephrase, or show the handle as a graphic.
- **Facts (B and C)** are verified or come from the owner; every name, date, number and the final fact has a source.
  Quote institutions only in their own words (the Science Museum says the Huggeford watch was used «apparently
  fraudulently» and calls its stone «ruby/glass»; it does not say «decorative»). A debunked myth can itself be the
  twist (10:10 is not Lincoln's time of death).

## 4. Delivery marks (for planning the pace)
In the planning script: `/` a short pause (~0.3 s), `//` a beat (~0.7 s), `///` the big silence before the twist
(1–1.5 s, once). `↓` drop and slow (the twist), `↑` lift (the start of the lesson or brand section). The voice stays
even and close; emotion comes from pace and pauses, not loudness.
In the film file they become punctuation the voice reads («…» for a held beat, «،» for a short one), the end of an
act (`pause: 0.35` on its last line), and `pause:` up to 1 s on the line before the twist. Never a speed change.

## 5. Direction
- **One idea per shot.** The picture shows exactly what the line says, when it says it; never the previous or the
  next line. Show, then say: the picture lands a beat before or on the word, never after.
- **Objects carry emotion.** Close-ups of hands, the dial, the crown, the second hand, the jewel, over wide shots.
- **Shot-size rhythm:** wide to establish, medium for action, close-up for every emotional beat, wide again for
  scale or the aftermath. Never the same size twice in a row on one subject. In the engine, `shots:` per line.
- **Density:** in a code or AI style, aim for 35–45 shots a minute (most lines get two: action and reaction, or
  wide and insert), at least half close-ups, no shot held over 3 s except the twist. In the engine, each scene
  changes shot size on the words that carry it.
- **The twist shot:** held longer (2.5–3.5 s), a slow push in, near silence, one real diegetic sound (a tick, a crown
  click). The revealed object is centred and the brightest thing yet; one accent colour reserved for the hero object
  (the ruby's red).
- **The callback:** the last shot rhymes with the first (the same object or angle, now changed).
- **Colour script:** one line per act (warm for the story, cool for doubt or conflict, the warmest frame at the payoff).
- **Continuity:** the same watch model, dial and character design in every shot.
- **Vertical 9:16:** the subject on the centre axis or the upper middle; nothing important in the top 8 % or the
  bottom 18 % (the app's buttons; make_film checks it).
- **Transitions:** the owner's rule (3b, 18e): dissolves inside an act, a push only into a new act, no whips.

Per shot, when a shot table is wanted: size and angle, camera move and speed, action, light and colour (or one line per
act), the cut in, and the sound.

## 6. Captions
2–5 words a chunk, timed to the voice, changing every 0.5–1.2 s; never a full sentence on screen; break after … . ؟ :
and never leave one word alone. The brand's caption style (gold active word; flat dark chips in the data look), just
above the bottom safe zone. A chunk with Arabic runs right to left; a chunk of only Latin letters or digits runs left
to right, or it renders reversed.

## 7. AI route prompts (only with the owner's yes to the credits)
One English line per shot: `[style lock], [shot size + angle], [subject + action], [setting], [light/colour], [camera
move], 9:16`. Every prompt starts with the same style-lock sentence and the same character and watch bible. No text,
logos or real brand marks in prompts; a real watch is never generated (it is a real photo, composited). Real brand
names stay in the narration.

## 8. Self-check before the script goes to the readers
- [ ] The first line is a physical image or the owner's question, and the first frame shows exactly that, named.
- [ ] Acts marked; read aloud as one paragraph, every line hands on; no line opens on a bare date.
- [ ] One `///` before the twist or final fact.
- [ ] (A) three specific modern examples, escalating toward «you, now».
- [ ] The last line reuses the central object (A, C) or is a true ironic fact or a question (B); the last shot rhymes
      with the first.
- [ ] Every fact sourced and quoted in its source's words; brand facts true.
- [ ] Within the length budget (about 10 spoken characters a second); a fact cut, never a bridge.

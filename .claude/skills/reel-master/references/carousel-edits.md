# What the owner's carousel edits teach

The owner, 2 Nov 2026: «I want you to understand every change I'm doing in the carousel so it can be updated for the
future, to keep it as a reference and learn from it». Every change the owner makes to a carousel (in the studio's text
editor, or asked for by slide in «تعديل») is logged here word for word, with the lesson drawn from it.

**Before writing any carousel, read «Apply every time» below and write to it.** It is the owner's taste, learnt.

## Apply every time
The lessons that stand, newest last. A lesson seen twice, or one the owner states as a rule, also goes into
`carousel.md` (and its check into `director/carousel.py` when a check can hold it).
1. **The cover's claim is true and respectful.** «لصانع مو الكل يعرفه», not «مايعرفه وايد»: the surprise without
   overstating it or making a respected maker small. (Halter 1 cover, v1→v2)
2. **A real person is a real photo** (theirs, the owner's, or their official press kit), never an AI drawing when a
   real one exists. Rule: `carousel.md`, People. (Halter 1, slides 1 and 3)
3. **The reader's question is big and pulls them in**: its own large line in the accent colour. Rule: `ask`.
   (rubies simple, slide 5)
4. **The end comes back to the cover's object** and asks about it: the Halter carousel opens on the Antiqua's price,
   so it ends on the Antiqua and a question about it. Rule: «the end answers the cover». (Halter 1, slide 5)
5. **A number is exact and says whose it is**: 17 jewels is the common count of a simple hand-wound movement;
   automatics carry more (the rotor). Rule: «Exact numbers, named». (rubies)
6. **The last idea teaches something the reader can use**: the fewest jewels a watch needs, and why each extra
   function adds parts, friction and jewels. (rubies, last slide)
7. **Less text**: 12–32 words a slide. Rule: `BODY_WORDS`. («قلل النصوص»)
8. **Text at the new size**: title 81, body 44, question 64, name 31, number 33, cover up to 86 px (10% over the
   first kit). On topImage and bottomImage the picture gives up the room. (2 Nov 2026: «the size of the text, it is
   small»)
9. **The precise word, in a written register.** The owner wrote «يحضر للبيت قطع من محركات» over «ويجيب للبيت قطع من
   مكاين»: the parts of trains are **محركات** (engines), not the vague «مكاين»; and a slide reads a touch more
   polished than speech («يحضر» over «يجيب»), still Kuwaiti. Pick the exact technical noun; don't open a sentence
   with a loose «و». (Halter 1 v6, the owner's own edit; watching the register for a second case)

## How to log an edit
The studio keeps each save word for word: the version's `changes[0].edits` (`[{where, field, key, before, after}]`)
and the owner's optional «ليش غيّرته؟» (`why`), and the same in the `inbox` note (`kind: edit`). When the inbox shows an
owner's edit, or a record has `edited: studio` with a version not yet in the log below:

1. Save the record (`ArtifactData` query with `out_dir`) and run `python3 tools/carousel/edits.py <record.json>`: it
   prints the entry (the changed words «before» ← «after», the full before and now, the «ليش»).
2. Add it under «The log», newest first, and write its **Lesson** in one or two lines: what the change says about the
   owner's taste (word choice, register, accuracy, tone, order, length, picture), general enough to apply to the
   next carousel, not just this sentence. If unsure what it means, the `why` field answers; don't ask the owner.
3. **Status:** `rule` (now in «Apply every time» and, if it holds generally, `carousel.md`), or `watching` (a single
   case whose reason isn't clear yet; promote it when it repeats).
4. Mirror this file to `.claude/skills/reel-master/references/`.

## The log

### 2026-11-03 · Halter · 1 v8 (the owner's own edit in the studio; logged 7 Nov)
- **الشريحة 1 · العنوان:** «—» ← «فياني هالتر»
  - was: ولد التروس
  - now: فياني هالتر ولد التروس
- **الشريحة 2 · العنوان:** «—» ← «شراء»
  - was: ساعة برج بعمر 11
  - now: شراء ساعة برج بعمر 11
- **الشريحة 3 · العنوان:** «شغل» ← «صنع ساعات لكن»
  - was: شغل مو باسمه
  - now: صنع ساعات لكن مو باسمه
- **الشريحة 3 · النص:** «ونماذج أولية» ← «—»، «باسمه هو.» ← «باسمه.»
  - was: في **1989** انتقل لسويسرا، وصار يصنع هناك ساعات معقدة ونماذج أولية لشركات كبيرة مثل بريغيه وكارتييه. بس كل هالشغل كان يطلع باسم الشركات، مو باسمه هو.
  - now: في **1989** انتقل لسويسرا، وصار يصنع هناك ساعات معقدة لشركات كبيرة مثل بريغيه وكارتييه. بس كل هالشغل كان يطلع باسم الشركات، مو باسمه.
- **Lesson:** a slide title names who or what acts: the person's name leads the cover («فياني هالتر ولد التروس»), and a title starts with its verb or noun of action («شراء ساعة برج…», «صنع ساعات لكن مو باسمه») rather than a bare fragment. Cut words that add nothing to the fact («ونماذج أولية», the closing «هو»).
- **Status:** watching

### 2026-11-02 · Halter · 1 v6 (the owner's own edit in the studio)
- **الشريحة 1 · النص:** «ويجيب» ← «يحضر»، «مكاين» ← «محركات»
  - was: فياني هالتر ولد قرب **باريس**. أبوه كان يشتغل على القطارات، ويجيب للبيت قطع من مكاين قديمة فيها تروس تدور. ومن هني، وهو صغير، بدا حبه للتروس.
  - now: فياني هالتر ولد قرب **باريس**. أبوه كان يشتغل على القطارات، يحضر للبيت قطع من محركات قديمة فيها تروس تدور. ومن هني، وهو صغير، بدا حبه للتروس.
- **Lesson:** the exact technical noun (train parts are محركات), and a slightly more polished written Kuwaiti; the
  sentence no longer opens on «و».
- **Status:** rule for the precise noun (9); watching for the register.

### 2026-11-02 · all carousels (asked in chat)
- «the size of the text, it is small… increase it about 10%»: title 74→81, body 40→44, question 58→64, name 28→31,
  number 30→33, cover 78→86 px.
- **Status:** rule (8); `const SIZE` in tools/carousel/carousel.mjs and `KIT.SIZE` in the studio, tested together.

### 2026-11-02 · الياقوت (asked by slide)
- «معلومه العدد انه اقل شي ١٧… و ٢٢ او شي جذي قصده اذا في روتر»: 17 is the common count; more with a rotor.
- Last slide: «اكتب اقل عدد من الجواهر الي تحتاجها الساعات و اي اضافة او تعقدية يزيد القطع وزياده الاحتكاك تساوي عدد
  اعلى من الجواهر».
- **Status:** rule (5, 6).

### 2026-11-02 · Halter · 1 v4, slide 5 (asked by slide)
- «خله ينتهي بساعة انتيكوا وسال يخصها».
- **Status:** rule (4).

### 2026-11-02 · الياقوت · بسيط v1, slide 5 (asked by slide)
- «دائما سوال القارىء يكون اكبر ويشد القارى على شان يضارك».
- **Status:** rule (3).

### 2026-11-02 · Halter · 1 v2, slides 1 and 3 (asked by slide)
- «استخدم صوره حقيقيه له افضل».
- **Status:** rule (2).

### 2026-11-02 · Halter · 1 v1, cover (asked by slide)
- «نخليها مو "الكل يعرفه" بدل "مايعرفه وايد"».
- **Status:** rule (1).

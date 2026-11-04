# Time Keeper house style (the published news)

The owner shared the team's news group: "take the ready and the final news to be used as a reference for the way of
writing the script… I just want you to see there is a middle ground between the formal Arabic and the Kuwaiti."
So the reference is the **published posts only** (1,792 final `#tk_` posts, 2024–2026), never the talk around them.
The counts below are from those posts. The posts themselves stay private with the owner; a script writer reads a
dozen recent ones before writing.

## The middle ground

The news is **light fusha that reads like speech**: news Arabic, but read in pause form and without stiffness.

- **Pause form, no case endings.** «حققت نجاح كبير», «يعطي الساعة مظهر رياضي» (adjectives without the alif of
  tanween: 0 «كبيرا / مميزا / جديدا» against 569 bare forms). A counted noun stays singular: «١٥٠ عام» (1,108
  «عام» against 10 «عامًا»).
- **Gulf grammar where fusha sounds stiff:** «ساعتين» (85, against 26 «ساعتان»), «وليس» for "not X" (55).
- **The news connectors:** مع (2,272), مستوحاة / مستوحى من (808), تأتي / يأتي (770), حيث (736), تتميز / يتميز
  (625), كما (311), أما … ف (243), بينما (166), تجمع بين (151). «الشركة» for a brand (453; الدار 58, العلامة 40).
- **Rounded numbers with «حوالي»** (97).
- **Kuwaiti is a light touch, not the base:** a closing question at most («شرايكم؟» 30, «ولا» 34, «تتوقعون»,
  «تشوفون», «شنو»); 60 of 1,792 posts ask the reader anything. The narration stays in the middle ground; a Reel may
  end on one short question. The owner rejected a full Kuwaiti narration («النطق الكويتي سيء خلك في خطتنا») and «يهال».
- Headlines are Brand + verb: «تطلق» (599), «تعيد» (60), «تضيف» (39), «توسع» (18).

## Words the news uses

| The news writes | Rarely |
|---|---|
| ستيل (1,128) | فولاذ (4) |
| مينا (1,660) | ميناء (146) |
| ذهب احمر (312) | ذهب وردي (66) |
| تكويك يدوي (375) | تعبئة يدوية (5) |
| مجموعة (931) | كيان (5) |
| مصنع (40) | منشأة (6) |

`story_check` only stops what the news practically never writes (فولاذ، تعبئة يدوية) and «يهال». Everything else
here is how to write, not a rule a check enforces.

## Kuwaiti words for the voice (the owner's choices, 3–4 Nov 2026)

The owner heard «السباحة» and Rolex ep1 as Saudi («النطق فيه لهجه سعوديه»). He compared each line as it was and in
Kuwaiti spelling learned from two Kuwaiti story Reels he sent, and chose the Kuwaiti spelling («ب احسن»). In a story Reel
told in Kuwaiti, write the word a Kuwaiti says, not the standard one:

| Write | Not | Note |
|---|---|---|
| عقب، عقبها | بعد، بعدها | «بس عقب چم يوم» |
| چم | كم | v3 says the «ch» itself; «چذب» too |
| يه | جا، دخل | «وهني يه هانز ويلسدورف» (the owner's fix) |
| ريال | رجل | on screen «ريال» (no shadda, the owner); said «رَيَّيال», number 7 of 7 spellings he heard (`brand/pronunciation.json`) |
| عطى | أهدى | |
| صدق | فعلاً | |
| عشان | لأننا | |
| ومضبوطة مثل ما هي | وما فقدت دقتها | «فقد» reads fusha (his review) |

Still no «گ» by hand (v3 says «تقول» as «تگول» in a Kuwaiti sentence by itself). The currency riyal is never said from
«ريال» (the dictionary makes it «رَيَّيال»); prices are in KWD (7b), and a line that must say riyals writes «رِيال».

**What spelling cannot do:** Faisal is an instant clone made from one sample, so it copies the voice, not the accent;
the spelling and a «[Kuwaiti accent]» tag moved it a little («التطوير مو كبير»), and so did the owner's own reading
converted to Faisal (ElevenLabs speech-to-speech, `eleven_multilingual_sts_v2`). A clearly Kuwaiti Faisal needs a clone
made from more Kuwaiti speech by the same speaker; that is the owner's call.

## Names, numbers and pronunciation in a Reel (the owner's choices, 1 Nov 2026)

- **Names are written in Arabic on screen**, spelled as the news spells them (بريغيه 94, فيليبس 42, سوذبيز 24,
  كريستيز 7; Latin «Phillips» and «Breguet» once each), `brand/names.json`. They are **said in their own language**:
  `load()` gives the voice the Latin name, and the **pronunciation dictionary** (`brand/pronunciation.json`, with the
  studio's pronunciation fixes) still decides exactly how every name and word is said. Nothing in the house style
  changes a pronunciation the owner has fixed. A film adds its people under `names:` (`{فياني هالتر: Vianney Halter}`).
- **Numbers on screen stay in English digits** (71,400 د.ك), as one word; the voice reads them as words (rule 9d).
  The news writes «د.ك» (1,608; «دك» 141).

## Words on screen

- Almost no punctuation: no full stops, few commas; «؟» only on a question; no emojis.
- Captions and one more block at a time (rule 18n).

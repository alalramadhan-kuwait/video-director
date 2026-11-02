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

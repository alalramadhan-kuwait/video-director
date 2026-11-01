# Time Keeper house style (the news group)

Learned from about 2,000 finished `#tk_` news posts (2024–2026) and the editors' corrections in the team's news
group. The owner: «تلاحظ الكتابة نص ما بين الفصحى والكويتي». A script is written the way the news is written.
(The full study, with dated corrections and example posts, stays private with the owner.)

## Register: news fusha, read in pause form, made light

- The base is plain news fusha, **read in pause form**: no case endings, no tanween, ever. «إطار» not «إطاراً»,
  «حققت نجاح كبير», «أكثر من ١٥٠ عام» (a counted noun stays singular), «٧١ ألف» not «ألفًا».
- Gulf grammar where fusha sounds stiff: «ساعتين» (not ساعتان), «كان متاح», «اسمهم» for a company's name,
  «وليس» for "not X" («باسمهم وليس باسمه»), «للبيت».
- No rhetorical particles: no opening «إنّ», no «لقد», «ثمة», «سوف» (use «سـ»), «من الجدير بالذكر».
- Connectors as the news uses them: و، مع، حيث، كما، لكن، أما … ف، بينما، بعدها. «تأتي الساعة بـ…»,
  «تتميز بـ…», «مستوحاة من…», «تجمع بين … و…».
- **Kuwaiti is a seasoning, not the base**: one or two touches a script, in the hook or the closing question
  («شرايكم؟ تستاهل ولا…؟», «تتوقعون نشوف…؟», «صج … بس»). Never a row of dialect verbs, never slang nouns
  (يهال، وايد، جذي) in the narration. The owner rejected a full Kuwaiti narration («النطق الكويتي سيء»).
- One idea per line, 6–14 words, each a full sentence («جملة مفيدة»).
- No flourish: no «تحفة خالدة», «اللافتة», «الأصيل», «غير مسبوقة», «تمنحه طابع دافئ». No literal translation of a
  press release: explain the idea behind the watch, not a list of parts.
- Nothing unofficial stated as fact (the news would not name a model a watch is "inspired by" when only others say so).

## Words

| We write | Not |
|---|---|
| تكويك يدوي | تعبئة يدوية، تدوير |
| ستيل | فولاذ |
| مينا (plural مين) | ميناء، دايل |
| ذهب احمر | ذهب وردي |
| سير / سيور، سوار | سترابات |
| مرجع | ريفيرانس |
| الروتر | الوزن المتذبذب |
| الريتروقريد، كرونوقراف، الفلاينق توربيون (Gulf ق for G) | الراجعي and other calques |
| تقويم دائم، مراحل القمر، مردد الدقائق، تعقيدة / تعقيدات | بيربجوال كاليندر |
| مصنع | منشأة |
| مجموعة / شركة | كيان |
| الإصدار الأخير | وداعي |
| النسائية | الأنثوية |
| الشركة (mostly; الدار / العلامة only for variety) | |
| حوالي، تقريبا، أكثر من، أي ما يعادل | an unrounded conversion |

## Names and numbers in a Reel (the owner's choices, 1 Nov 2026)

- **Names are written in Arabic on screen**, spelled as the news spells them (فيليبس، بريغيه، باتيك فيليب،
  أوديمار بيغيه، كريستيز، سوذبيز، تاق هوير…; `brand/names.json`), and **said in their own language**: the
  film's `load()` gives the voice the Latin name (`brand.to_voice`). A film adds its people under `names:`
  (`{فياني هالتر: Vianney Halter}`). Abbreviations a viewer can read (GMT, MB&F) may stay Latin, explained (rule 6d).
- **Numbers on screen stay in English digits** (71,400 د.ك), as one word (rule 18b); the voice reads them as words
  (rule 9d). Prices in KWD first, rounded; «د.ك».
- Plain letters on screen, no tanween; diacritics the voice needs go in `say:`.

## Layout of words on screen

- Almost no punctuation: no full stops, few commas; «؟» only on a question; no emojis.
- Captions and one more block at a time (rule 18n).

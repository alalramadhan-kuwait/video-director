# The Kuwaiti voice guide: 50 rules, and which ones Faisal follows

The owner's guide (4 Nov 2026, «الدليل الشامل لقواعد اللهجة الكويتية لنماذج الصوت»): the target is urban Kuwaiti as
told in a story, not Bedouin speech and not Kuwaiti news fusha. Four layers: the letters, the vowels, the grammar and
words, and the rhythm. His method, which we follow:
1. Classify each rule (letters, vowels, morphology, phrasing, rhythm) and say whether it is Kuwaiti, shared Gulf, or a
   guess. Compare with Najdi in particular, and remember Kuwait is close to the Eastern Province.
2. Test each rule that can be heard on five sentences, in the plain spelling, a marked spelling and a phonetic one.
3. Record every version with the same voice, settings and seed (Faisal, `eleven_v3`, stability .5, similarity .8,
   speed 1, seed 1234), so the spelling is the only change, and put them side by side for the owner's ear.
4. Keep the best spelling per phenomenon, try it on new sentences, and note the exceptions and the words whose
   meaning changes when a letter is swapped.
5. **Keep the text as written.** Rules change only the voice text (`say`); the screen keeps normal spelling. Spelling
   rules stay apart from performance tags (`emotion`).
6. **No rule is adopted until it is tested and the owner approves it.** Never apply a letter swap to every word
   (not every ج becomes ي, not every ق becomes G), and never adopt «وقتهه» or «وراهها» as a general rule unheard.

Priorities: **P1, the identity** (ج/ي, ك/چ, ق and its sounds, the attached pronouns, the short vowels); **P2, how
natural it is** (words run together, doubled letters, stress, dropped vowels, the long vowels); **P3, the narrator**
(the tone of a question or surprise, the pauses, the pace by scene).

## Status (✓ adopted by the owner's ear · ◐ written that way, not yet tested · ○ not yet · ⏳ on the test page)
| # | Rule | Status |
|---|---|---|
| 1–2 | ج → ي in certain words | ✓ «رَيَّيال»، «يه» · ✓ (4 Nov) يديدة، ويهه، ياب، يوعان · «جلس» is neither: write «قعد» |
| 3 | ج kept in others (جامعة، جهاز) | ◐ |
| 4 | ك → چ in certain words | ✓ چذب · ✓ (4 Nov) «چذي» (over جذي and كذا); «السمك» said «السمْج» (his own spelling) · kept: كان، كبير، **كم** (he chose the plain «كم» over «چم»: write «كم» from now on) |
| 5–6 | the feminine «you» as چ (شلونچ), the masculine kept | ✓ (4 Nov) شلونچ، عندچ، قلت لچ: whenever a line speaks to a woman, its `say` writes چ |
| 7 | ق said G | ✓ never write «گ»: v3 says it the Kuwaiti way by itself (owner's reviews, 2 Nov) |
| 8 | ق → ج in certain words | ✓ جدام، ✓ (4 Nov) الطريج · kept with ق: قريب، صديقه، دقايق |
| 9 | ق kept in formal words | ◐ |
| 10–12 | ض/ظ close; ث and ذ kept in many words | ○ (a ث word read the fusha way is reworded: «ثبت» → «انحسب لها») |
| 13–15 | the feminine «ـها» | ✓ a sukun on the letter before it (وقتْها، بعدْها); «ـهه» rejected after his ten-spelling test |
| 16 | the masculine «ـه» | ◐ |
| 17 | doubled letters | ✓ the shadda written (كمّلتها، خلّها) |
| 18–19 | natural long vowels; a stretched vowel for surprise | ○ |
| 20–21 | dropped first short vowels | ✓ (4 Nov, 5 of 5) صْغير، كْتاب، طْويل، سْنين، بْعيد; a new word of the same shape is tried on the review page before it joins |
| 22 | stress moving with the pronoun | ○ |
| 23 | words run together | ✓ (4 Nov) مافي، شسالفة · kept apart: ما أدري · إن شاء الله either way · «من وين جاب»: neither, «جاب» must be «ياب» |
| 24 | a vowel lengthened at a stop (شنو؟ صج؟) | ○ |
| 25–28 | pronouns (أنا، إحنا، إنتوا، هم، كتابچ) | ◐ |
| 29–30 | «قاعد» for the present | either way (4 Nov): the script decides |
| 31–32 | the future with «راح» or «بـ» | either way (4 Nov) |
| 33–34 | ما for verbs, مو for nouns | ◐ |
| 35–36 | ماكو، أكو | ✓ (4 Nov) «أكو» over «فيه», «ماكو أحد» over «محد» |
| 37–46 | شنو، منو، شلون، كم، وين، ليش، أبي، چذي، هذيل، عيل | ◐ شنو، منو، شلون، أبي · ✓ (4 Nov) چذي، «عيل» over «إذن» |
| ep2 | the owner's Rolex ep2 review (6 Nov) | ✓ «بعد» over «عقب», «مو كافي», «القليلة», «إيدك», «محرك»; by ear: «طِلْعت» (she went up), «تِعَرْف», «يِقِلّ» |
| 47–50 | the narrator's rhythm (questions, pauses, pace, the stressed word) | ○ needs Kuwaiti reference recordings, not spelling rules |

**How the results reach the voice:** the words he chose for their sound are in `brand/pronunciation.json` (with و ف ب
in front), so every `say` gets them by itself and the screen keeps the normal spelling. The words he chose as words
(قعد، أكو، ماكو أحد، مافي، شسالفة، عيل) are written in the script, screen and voice alike. Before a new take, check the
`say` of each line against the list; the pronunciation page shows what the voice was given.

The Kuwaiti word table (house-style.md) and the numbers in Kuwaiti words (خمسطعش، إحدعش، ألف وتسعمية) are adopted.
**The limit:** Faisal is an instant clone from one sample; it copies the voice, not the accent. Rules move the
pronunciation closer; the full Kuwaiti rhythm needs a clone built from longer Kuwaiti speech by the same speaker.

**The test page** (4 Nov 2026, P1 first, 33 sentences and 67 recordings; answered the same day) is the studio's decisions page; answers land
in its `answers` collection as `kw50-<rule>-<n>`. Each adopted spelling goes into the table above and into
house-style.md, with the date.

References the owner gave: Shamlan Al-Qenaie, «Kuwaiti Arabic: A Socio-Phonological Perspective» (Durham e-theses);
the Dialectologia study of the Kuwaiti ك → چ; «Characteristics of Written Kuwaiti Arabic» (Kuwait University).

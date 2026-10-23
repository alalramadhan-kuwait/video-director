# Storytelling and production rules (the owner's standards)

The owner set these standards through their reviews of the Panerai film. Apply all of them to every film without being
asked: they are what any good documentary maker does. `tools/make_film.py` checks the ones marked ✓ and prints a
`story:` line. A film is not sent until that line says «all rules kept».

## The story
1. **In order** ✓ — tell events in the order they happened, in acts (beginning → turning point → mission → after).
   A year never goes back unless the line is a deliberate flashback (`flashback: true`).
2. **Connected** — each act and each scene leads into the next: one thing causes or prepares the next. The viewer must
   never wonder why we are suddenly somewhere else.
3. **Every change of scene is led into** ✓ — the line opens with a connective or a sentence that prepares the change:
   «لكن البحرية احتاجت…», «غير أن الراديوم نفسه أخفى سرًّا مظلمًا…», «وبينما كان العالم يكتشف خطر الراديوم…»,
   «ثم انتهت الحرب…». Only the final echo may stand alone (`closing: true`).
4. **Explain why** ✓ — every change (a new material, a new design, a new partner) says its reason (`change: true` +
   `because:`), in the narration itself: why Rolex, why the crown bridge, why radium was replaced.
5. **Feelings** ✓ — name the feeling of the lines that carry it (`mood:` mystery, fear, sadness, tension, joy, wonder).
   **Sadness for human moments always**: people who suffered, were deceived, died, were captured. Make it human:
   who they were, what they were told, what happened to them («قيل لهنّ إنه آمن… فتساقطت أسنانهنّ… ورحلن جميعًا»).
6. **A strong, honest hook** and a closing line that echoes it.

## The facts
7. Every claim has a source in `sources:`; the line names its source numbers.
8. **Precise words**: say exactly what the source says. «حصلن على تعويض» (a settlement), not «كسبن القضية»;
   «عاملات شابّات», not «فتيات صغيرات», unless the source says so.
9. **Never imply a link that does not exist.** Two similar things are named apart: the American dial painters used
   Undark, not Panerai's Radiomir; the link is radium itself. Before writing «the same light/the same watch», check
   that it is literally the same.
10. A claim the sources only believe or call likely is said as a belief: «يُقال…».
11. Contested dates: say only the part all sources agree on (the decade).

## The pictures
12. **A historical event is shown with a historical photograph** ✓ (`event: true` → `archive_photo`), licensed, with
    the author and licence on screen and a card saying when and where. When none exists, say why (`no_photo:`).
    Search Wikimedia Commons in English with the place's or object's own name (e.g. «Alinari Ponte alle Grazie» for
    the bridge of Panerai's first shop).
13. If the exact thing has no free photo, show the nearest true thing and **say what it is** («الجسر الذي كان عليه
    أول محل»), never pretend.
14. **Each scene shows only what is said in it** ✓: every banner, card, row and label shares words or numbers with
    that line's narration. Never a recap timeline of other lines, never a modern product under a historical claim
    (label modern watches «طراز حديث» and use them only where the line talks about the watch itself).

## The look and the sound
15. **A world for every scene** (`set:`): underwater, sea_night, florence, workshop, radium, archive. A map or a
    full-frame photo is the world itself (sound only).
16. **A city named in the story arrives with `city_zoom`**: the smooth flight from the country, its colours and its
    landmarks rising, its name. Add the city to `director/studio/cities.py` if it is missing.
17. **Maps are in colour** (the atlas look): the story's country in gold.
18. **Effects and sounds**: templates carry their own sounds; music from the library is ducked under the voice; one
    credit line for the music goes in the post caption.

## Delivery
19. Look at every still in `<out>/scenes/` before sending (text cut, overlaps, a stamp too faint on a dark scene).
20. 1080×1920, about −14 LUFS, at most `export.max_mb` (26 MB) — make_film compresses harder by itself if needed.
21. Send the film with its sources, photo credits and music credit (`credits.txt`). The draft voice is labelled as a
    draft; the final narration is OmniVoice.

## Working with the owner
22. Reply in Arabic (Kuwaiti is fine), short: what is done, what remains, what you need.
23. Do the whole film yourself; the only approval is the finished film before publishing. Never paid generation
    without an explicit yes.
24. In the video-director repository, merge your own pull requests once the tests pass, without asking.
25. When the owner corrects something, fix it in the film **and** make it a rule here (or in `story_check`), so it is
    never needed again.

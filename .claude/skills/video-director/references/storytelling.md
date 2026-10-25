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
6. **The film opens where the story begins** ✓ — its first place and year, flown into with `city_zoom` («في Florence،
   عام 1860»), then the story in order. The owner did not like a teaser opening that sums the film up over a drawing
   (Panerai, the patent on blueprint paper): no summary before the story, never a photo first. The closing line may
   still echo what the story became. A real drawing from the archive (`template: blueprint`, e.g. a US patent drawing,
   public domain) belongs where the story reaches it; **never an invented cartoon or clip-art drawing**: the owner
   finds it childish.
6b. **Never tie the brand itself to something bad.** The hook and the closing describe the brand by what it did for
   people («ساعة صُنعت لرجال يعملون في عتمة البحر»), not by the harm of a material it once used («وُلدت من ضوء قاتل»).
   The dark chapter is told in the middle, as part of the story, about the material and the people it hurt.

## The facts
7. Every claim has a source in `sources:`; the line names its source numbers.
8. **Precise words**: say exactly what the source says. «حصلن على تعويض» (a settlement), not «كسبن القضية»;
   «عاملات شابّات», not «فتيات صغيرات», unless the source says so.
9. **Never imply a link that does not exist.** Two similar things are named apart: the American dial painters used
   Undark, not Panerai's Radiomir; the link is radium itself. Before writing «the same light/the same watch», check
   that it is literally the same.
9b. **Foreign names and English words in English letters** ✓ — in the script, on screen and to the voice, as in the
    Gérald Genta films: «Panerai», «Rolex», «Oyster», «Marie Curie», «Ponte alle Grazie», «Florence»; the voice reads
    them as they are (`narration.keep_latin` in the brand config). Arab places keep their Arabic name (الإسكندرية).
    Mind the article: an Arabic «ال» before a Latin word is lost when spoken; keep that word Arabic in that line.
10. A claim the sources only believe or call likely is said as a belief: «يُقال…».
11. Contested dates: say only the part all sources agree on (the decade).

## The pictures
12. **A historical event is shown with a historical photograph** ✓ (`event: true` → `archive_photo`), licensed, with
    the author and licence on screen and a card saying when and where. When none exists, say why (`no_photo:`).
    Search Wikimedia Commons in English with the place's or object's own name (e.g. «Alinari Ponte alle Grazie» for
    the bridge of Panerai's first shop).
12b. **Every scene has a related photo** ✓ — a photo template, or the photo behind the words (`photo:` on a line of
    words, a stamp or a number), or a city zoom. A scene with no picture is not sent.
12c. **The photo is of the time the line speaks of** ✓ — every photo carries its `year:` and make_film warns when it is
    more than 15 years from the years said. A modern photo only when the line speaks of today («حتى اليوم»); an old
    photo never illustrates something new. Check who is in a photo: a portrait under a famous name may be someone
    else with the same name (the «Luigi Durand de la Penne» file on Commons is a 19th-century namesake).
12d. **When a line names what someone made, show that thing**: «صارت تصنع أدوات دقيقة للبحرية» shows the instruments
    themselves (Panerai's depth gauge, compass, torch), not the city around them. Search Commons for the object with
    the maker's name («Panerai depth gauge»).
12e. **A person on screen is introduced and seen** ✓: a portrait carries `person: <name>` on its photo; it is shown
    with `archive_photo` and the name in the banner or the card, never as a dimmed photo behind words (the words land
    on the face and the viewer does not know who it is). The narration names them with who they are («العالمة ماري كوري»).
12f. **A group in the story is followed to its end**: who they were, what they did, what happened to them and when
    («خمس عاملات… أطباؤهنّ يقولون إنهنّ يحتضرن… حصلن على تعويض… ورحلن الخمس»), one line for each step, never a
    clause the viewer can miss. Show the document of the time when there is one (the 1928 newspaper page).
12g. **Old newspapers are evidence**: Library of Congress, Chronicling America (US papers published before 1930 are
    public domain). Search the page, crop the headline and the paragraph that proves the line, credit paper and date.
    When the injury or event itself has no free photograph, say so to the owner and show the newspaper instead;
    never a modern medical photo of someone else.
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
18b. **A number is shown as the number** (learned from video-ad-editor): a count or a measure → `stat_counter`, «X of
    every N» → `part_of_whole`, a rise or a fall → `trend_chart`, then and now → `compare_bars`. The number lands on the
    word that says it (`land` = when the voice says it). Only sourced figures, with their `source`; never invent a
    number to fill a chart.
18c. **One hero per scene, sounds on moments**: one main picture in a scene (a second only to support it). A sound
    marks something that happens (a number lands, a stamp, a new scene), never every word: about 15 a minute at most,
    and half a second of quiet before the most important line.
18d. **A written hook, when the opening has no words of its own** (`hook: {text, em, dur}` in the film file, from
    video-ad-editor; a city zoom's name is already the hook): a few of the opening line's own words (make_film warns when most of them are not said), `em` in gold, «|» breaks the
    line. The captions wait until it has gone: two texts at once and the viewer reads neither.
18e. **Cuts land on the music's beats** ✓: make_film shifts the music (later in its track, or a moment's late entry)
    so the most scene changes fall on a beat; nothing in the film moves. `beats: punch` adds a small camera push to the
    scenes that start on a beat.

## Delivery
19. Look at every still in `<out>/scenes/` before sending (text cut, overlaps, a stamp too faint on a dark scene);
    for a quick look at many scenes, one contact sheet of about six frames costs less than six separate images.
20. 1080×1920, about −14 LUFS, at most `export.max_mb` (26 MB) — make_film compresses harder by itself if needed.
20b. **Where it is posted decides the delivery** ✓ (`platform:` in the film file, else the brand's `export.platform`;
    `director/platforms.py`): Reels and Shorts up to 3 minutes for sure, TikTok up to 10 (1–3 is best), WhatsApp in
    parts under 16 MB cut between scenes. No words under the app's buttons: make_film checks every 0.2 s as drawn and
    must say «nothing under the app's buttons». Reels and TikTok get a separate `cover.png` (the hook's frame).
    **A film longer than its platform allows is cut to fit before it is sent** (the owner, on Panerai at 3:22 for
    Reels): drop whole lines whose neighbours still lead into each other, never the reason for a change or the end of
    a group the story follows (12f), and drop the photos and sources only those lines used.
21. Send the film with its sources, photo credits and music credit (`credits.txt`). The draft voice is labelled as a
    draft; the final narration is OmniVoice.

## Working with the owner
22. Reply in Arabic (Kuwaiti is fine), short: what is done, what remains, what you need.
23. Do the whole film yourself; the only approval is the finished film before publishing. Never paid generation
    without an explicit yes.
24. In the video-director repository, merge your own pull requests once the tests pass, without asking.
25. When the owner corrects something, fix it in the film **and** make it a rule here (or in `story_check`), so it is
    never needed again.
26. **The narration voice is OmniVoice** (the owner's choice, after hearing VoxCPM2 and the draft voice): read every
    film with it (`tools/voice_mac.sh films/<name>.yaml`, or `--engine omnivoice --lines-dir`) and make the film with
    `--voice-dir`. The owner has settled the question of its licence: do not raise it again.

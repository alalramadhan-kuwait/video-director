# The topic as a carousel (the owner's tk-topic-carousel kit)

The owner, 2 Nov 2026: «the option to generate the topic as a carousel instead of video if required… integrated into
dashboard with availability to save along with caption». A topic becomes a **Reel**, a **carousel**, or **both**
(`format:` at step 1; the studio's «ابدأ» sends it). A carousel is the written companion of a Reel: the same topic,
read in six swipes.

**First read `carousel-edits.md`** («Apply every time»): every change the owner has made to a carousel, word for
word, and what it teaches. Log each new one there (the owner: «I want you to understand every change I'm doing in the
carousel… to keep it as a reference and learn from it»).

## What it is
A TK cover (a full-bleed picture, the TK overlay, two headline boxes bottom-right, at most 73 characters together),
then **4–5 written slides**, 1080×1350 PNGs: one idea each, a title of 2–4 words, a short body of 12–32 words (as
little as the idea needs; one or two key words in `<b>`, the accent colour), and one large picture that never touches
the text.

**Three things at once, in every carousel** (the owner, 2 Nov 2026): it pulls the eye, it is easy to understand, and
it is exactly right. The aim: someone who knows nothing about watches understands it and enjoys it; a watch lover
learns something accurate and new. No one style is forced on every topic.
- **The cover** catches the eye in whichever way suits the topic: something familiar with a new or unexpected fact
  about it («في ساعتك ياقوت حقيقي»), or something strange that makes people want the reason. Never mystery alone: the
  picture is clear and understood at first glance.
- **Pictures that help.** A real, complicated photo (a movement full of parts) is used only when it helps the reader;
  otherwise a simple, beautiful drawing of the idea: two generic movements with their jewels, a pivot wearing its
  hole, a jewel bearing, a flame. A drawing never shows a real model, and never suggests more than the text says (two
  movements of 17 and 25 jewels are drawn as equals: the count alone does not make one better).
- **Explain by picture.** Motion, friction and what a part does are drawn; the text is cut to what the drawing cannot
  say, and detail that does not help the reader goes.
- **Exact numbers, named.** A figure that belongs to some movements is given as a range or with the movement it
  belongs to (a balance beats 5 to 8 times a second, by movement), never as if every watch had it; a breakdown is the
  common one, said so (17 jewels: 5 balance = 2 holes, 2 caps, the impulse jewel; 4 pallets = 2 stones, the arbor's
  2; 8 for four wheels, 2 each).
- **Each slide gives something useful and leads to the next.** Not every slide needs a puzzle or a number.
- **The end answers the cover plainly** (more jewels is not by itself a better movement: what matters is where they
  are and what they do), then asks the reader. The layouts rotate (topImage, rightBleed, bottomImage, leftBleed,
bigCorner), never the same twice in a row; a portrait uses rightBleed or leftBleed. The order follows the Reel's arc:
problem → history or mechanism → twist → answer, the last slide ending on the viewer's question.
Each slide leaves the reader wanting the next (the owner, of Altivère's jewels Reel: «more organized as flow and
ideas»): a side story that does not serve the topic's question is cut, however good. That question is
its own line, `ask`, set large in the accent colour under the body, and it pulls the reader in to answer (the owner,
2 Nov 2026: «دائما سؤال القارئ يكون أكبر ويشد القارئ عشان يشارك»): a real question about them or their watch, not a
teaser. Only the last slide asks; its words count in the slide's 12–32. Paper ground, the TK
green as the one accent, the TK overlay on every slide.

## The owner's rules for a carousel
- **Time Keeper's identity, on every carousel** (the owner, 8 Nov 2026, with a real TK post: «you are different from
  timekeeper or original design»):
  - **Green** `#2C6048` is the secondary colour: key words, the reader's question and «اسحب للمزيد». It replaces the
    per-topic accent (the renderer's default; don't set `accent`).
  - **The font is Bahij Helvetica Neue** (Bold for titles, Roman for body), in `brand/carousel/` beside the overlay
    (outside git; from the public Bahij font set, e.g. github.com/shamshadzaheer/pashtowebfonts).
  - **The slide number sits in a black box with white text** («01 / 19»), no line under it.
  - **A grid cover** is the other option for a list (the owner, 8 Nov 2026): `tools/carousel/grid_cover.py` puts as
    many whole photos as fit and look good (4×3 by default) under the logo band, and the cover sets `"gap": 60` so the
    headline and «اسحب للمزيد» sit low. Offer it beside the single-watch cover as an `asks` choice.
  - **The cover:** the watch on the photo's own ground, the headline in black boxes, and the green «▶▶ اسحب للمزيد»
    under them, on the ground, never over the watch.
- **A news carousel is in Fusha** (the owner, 8 Nov 2026, GPHG 2026: «استخدم العربية الفصحى»): `"language": "light"` (عربي خفيف, no dialect words), the reader's question too.
- **The language is Kuwaiti** by default (the kit), or the film's `language:` from the script library; watch terms in
  English. `director/carousel.py` holds the slides to the language's words.
- **Facts verified** as for a Reel (reuse the Reel's sources); institutions in their own words.
- **People:** a slide about a person shows that person, as a real photo: from the owner's `people/` portraits, one they
  attach, or the person's own official press kit (made for the press; credit it «ملف X الصحفي» in the caption). A real
  photo beats an AI drawing of them (the owner, 2 Nov 2026: «استخدم صوره حقيقيه له افضل»). Never other photos of real
  people from the web: when none of those has one, list the missing names to the owner in one line, and meanwhile show
  the slide's object with the person's name and verified years under the title (`name`). A photo with its background
  stays a rounded photo (rembg frays hair and faces), padded so it sits inside the slide.
- **Images:** drawings made for the topic (above), frames of the matching Reel, the owner's own photos, free-licence
  photos, or Higgsfield (credits, confirm the cost first); never brand press photos from the web. A photo is a clean cut-out
  (`var/cutenv/bin/python tools/cutout_photo.py frame.png cut.png`). The cover is a full-bleed photo.
- **A watch is never cut out of its photo** (the owner, 8 Nov 2026: «Always when you remove the background you remove
  part of the watch. To avoid this use the same color of the background as the color of the post»). Keep the photo
  as it is and set the slides' `paper` to the photo's own ground (a press photo on white: `"paper": "#ffffff"`), so
  the photo melts into the slide. When the photos have different grounds, use the most common one as `paper` and give
  the others a rounded frame; never the background remover on a watch. `check()` refuses a watch slide whose picture
  has transparency.
- **A watch or a movement is shown whole** (the owner, on the rubies carousel: «محرك جزا كبير منه رايح»): the
  background remover can eat the dark parts of a movement, and a bleed layout pushes half of it off the slide. A round
  watch or movement is cut with a circle around its case (geometry, not the remover); look at the cut-out before
  rendering; a watch never takes rightBleed, leftBleed or bigCorner (they cut it), only topImage or bottomImage.
- **A news carousel** (a launch, an awards list) is the exception to «4–5 slides» and «never brand press photos»
  (the owner, 7 Nov 2026, GPHG 2026 winners: «استعرض الساعات الفايزة كخبر وكل وحده فازت باي فئة», then chose 20
  slides and the official images): one watch a slide, up to 19 after the cover (Instagram's limit is 20), the
  category as the title, `Brand · Watch` as the `name` line, one verified fact in the body. The images are the
  official ones the organiser or the brand publishes for the press (the watch's own page on gphg.org), credited in
  the caption; never resellers or social posts. A prize that is not a watch goes in the caption.
  Set `"news": true, "big": true` (the owner, 8 Nov 2026: «We need to reduce the text and increase the watches
  size»): the body is one short fact (3–14 words), the picture takes the rest of the slide (`big` lets topImage text
  sit as low as it fits and keeps the picture under the logo band), and each photo is trimmed to the watch: the white
  margin cut away, and on a long strap the strap ends, never the case.
- **A story runs in order, one slide into the next** (the owner, 8 Nov 2026, on SpaceOne × Baltic v5: «القصة مو
  متصلة ومتسلسلة»): when the carousel tells a story, the slides follow time (who, then the meeting, then the people,
  then what they made, how it works, its launch), each body opens with a word that ties it to the slide before
  («وهناك»، «وبعد خمس سنوات»، «لكي تقفز»، «وتحت الموديول»), and nobody appears before the slide that introduces
  them. The payoff the cover promises (a prize, a record, the answer) is the last slide, never the first: a cover «من
  لقاء أصدقاء… إلى جائزة» ends on the prize. Read the bodies alone, in order, before rendering: they must read as one
  paragraph.
- **Caption:** two lines in the same language. **No hashtags and no sources in a caption, ever** (the owner, 8 Nov 2026: «in the caption, always remove the hashtag and sources»). The sources and credits go to the owner beside the post (`sources`, `credits`), never in the text he posts; a licence that requires a visible credit (CC BY / BY-SA photos or music) gets it as a small line on the picture or the end card instead.

## The awards style: a list of winners (learnt 8 Nov 2026)
The owner showed a competitor's GPHG carousel as the model for lists («learn their style, but apply our identity… for
future reference»). Five slides carry twenty winners:
- **Cover:** the grid cover (`tools/carousel/grid_cover.py`, `"gap": 60`), the top winner first (top-right) with a
  green seal on it (`"badge": {"text": "الإبرة الذهبية", "sub": "2026"}`), the headline in black boxes.
- **The top winner alone** (`"type": "hero"`): the watch large in an outlined frame, the prize as the title, then
  BRAND (caps), model and `REF.`, and the green seal.
- **Six cards a slide** (`"type": "cards"`, up to 6): each an outlined card with the category on top in green, the
  watch, BRAND, model and `REF.` (the official reference, from the organiser's page; leave it out when there is none).
- **One header on every slide** (`"head"`), the number in its black box beside it; the TK overlay as always.
- TK's identity throughout: white ground (the photos'), green `#2C6048` outlines and categories, Bahij, no cut-outs.
Use it for any list of many pieces (awards, launches of a fair, a brand's new references); keep the one-watch slides
for a story.

- **A photo on its own ground** (a steel table, a grey portrait, a wrist shot): set the slide's `"paper"` to the
  photo's edge colour, so the paper matches the photo (the owner: never cut the watch out); a dark paper turns the text
  and the logo white and the key words light green. A brand's transparent packshot is laid on white and cropped to the
  watch first. A cover whose headline sits on a darker part than its top takes `"swipe": "light"`.
- **Seamless, never a box** (the owner, 8 Nov 2026, on SpaceOne v4: «make sure the boundary seems seamless… increase
  the size of the picture, that it will seem as one integrated»): a photo on its own ground becomes the slide. Run
  `python3 tools/carousel/full_photo.py PHOTO OUT.jpg [--focus 0.4]`: it fills the width from the top edge, fades its
  lower part into the colour it ends in, and prints that colour; set the slide to `"layout": "full"`, `"image": OUT`,
  `"paper": <that colour>`, and the text sits on the colour. `check()` refuses a slide with its own paper in a boxed
  layout. A photo on white (the organiser's or a packshot) stays on white paper, which is already seamless.
- **A different image on every slide** (the owner, 8 Nov 2026, SpaceOne: «Try to use different images for each
  slide»): the brands' own press and product pages usually hold more than the organiser's two or three (packshots,
  caseback, wrist shots, parts laid out, the founders' portraits).

## The price-list style: one watch a slide, its price (learnt 8 Nov 2026)
The owner showed @thewatchmenu as a style to learn («They have good style learn it»). What carries their account: a
famous name or a price figure on the cover, one watch a slide, the same closing card on every post; their sponsored
and brand-push posts do worst. Their navy and cream, script logo and italic serif are theirs; TK keeps its own identity.
- **Cover:** the grid cover (`grid_cover.py --cols 3 --rows 2`, `"gap": 60`), a short headline (2–6 words a line)
  that carries the number or the name («من 1,140 دينارًا… إلى أكثر من مليون»).
- **One watch a slide** (`"type": "price"`): the header line and number box, the watch whole on its white ground, a
  green rule, then the category (`title`), BRAND, model, `REF.`, the price in dinars large (`"price": "≈ 1,140 د.ك"`)
  and the official price it comes from in a small line (`price_note`: «السعر الرسمي 3,000 فرنك سويسري»). Prices are
  the organiser's or the brand's own published price; say the rate is approximate and which day it is from.
- **The last slide** is the TK green card (`"type": "end"`: title, one line, the handle), never a question (a news
  carousel ends without one); the question stays in the caption.
- **Or a ranking chart as the cover** (the owner, 8 Nov 2026: «نخليها غراف بالترتيب من اغلى الى الاقل»):
  `"cover": {"type": "chart", "title", "sub", "rows": [{"label", "model", "image", "value", "text"}]}`, one TK-green
  bar a piece from the most expensive down, linear so the gap shows (never under 4px), the value at each bar's end;
  then the watch slides in the same order. 6–20 slides in all.
- Formats to borrow: «غالية أو في المتناول» (an icon beside a watch with the same idea for less), the shop's price
  beside the market's, a brand's story as a timeline. A brand we sell is still an indirect ad.

## The script before the slides (the owner, 9 Nov 2026: «for the carousel, I want to be able to review the whole carousel script before you generate the posts»)
A carousel's words go to the owner as a script **before any slide is rendered**, the way a reel's script comes
before its voice. The order is: the idea and research, the direction or the style sample, **the script**, then the
slides.
- **What the script holds:** every word that will be on the post, one line per unit, in order:
  - `الغلاف: <top> / <bottom>`;
  - one line per slide, `شريحة NN · <title> (<name>): <body>`, plus ` سؤال القارئ: <ask>` on the slide that has one;
  - `الكابشن: <caption>`, with ` ¶ ` between its paragraphs.
- **Where it goes:** the film record's `script.lines` (`[{n, text}]`), version `نص vN`, `state: 'waiting'`, no
  `slides` yet. The studio shows it in the script card, where he edits any line («اضغط أي جملة») or approves.
- **Before he sees it,** run `tools/house_check.py` on the spec and caption (the caption rules, the story order, the
  feed window). He reviews words only after they pass.
- **After he approves:** render exactly the approved words. His edits come back as `script_edits` by line number:
  apply each one to that unit of the spec, re-run the house check, and post the next `نص vN` if a rule now fails.
- **A text change after the slides exist** goes the usual way (slide numbers, or «عدّل النص بنفسك»). It does not
  reopen the script step.
- **A style sample** (cover and two slides) may come before the script. Its words are a draft, and the script step
  still follows it.

## Make it
**The house rules gate** (the owner, 8 Nov 2026: «after writing a text, is there a gateway that will check all those rules… so all those edits will not go to waste»): every owner correction a machine can check lives in `brand/house_rules.yaml`. Run `python3 tools/house_check.py <film.yaml | carousel folder | caption.txt> --fix` after writing any script, slide or caption and before the owner sees it; rewrite what it flags (or, when a flagged word is right in that sentence, list it under the film's `rules_ok:`), and confirm its «remember» lessons. `record_flow.py` refuses a paid take and `make.py` refuses to render while a rule is broken.

Folder `carousels/<name>/` (outside git when it holds third-party photos): `spec.json`, the images, `caption.txt`.

```json
{"language": "kuwaiti", "accent": "#a3172e",
 "cover": {"top": "ليش داخل ساعتك", "bottom": "ياقوت حقيقي؟", "image": "cover.jpg", "box": "light"},
 "slides": [{"title": "النحاس يتآكل", "body": "…", "image": "cut1.png", "layout": "topImage"},
            {"title": "لندن، 1704", "name": "Fatio de Duillier · 1664–1753", "body": "…", "image": "cut2.png"}]}
```

**Text sizes** (the owner, 2 Nov 2026: «the size of the text, it is small… increase it about 10%»): title 81, body 44,
reader's question 64, name 31, slide number 33, cover lines up to 86 px (they shrink to fit 940 px). One table,
`const SIZE` in tools/carousel/carousel.mjs, the same as `KIT.SIZE` in the studio's editor. On topImage and
bottomImage the text is measured first and the picture takes the room left (at least 420 px tall); the renderer
prints `WARN:` when the text runs off the slide, into a picture, or squeezes it: shorten the text, never the type.

`python3 tools/carousel/make.py carousels/<name>` checks it, renders `out/01_cover.png … 06_slide.png` and a contact
sheet `out/sheet.jpg`: look at it (text never on the image, nothing under the top band, Arabic right to left, Latin
not reversed, the cover logo readable). The TK overlay (`Black_temp.png`, `White_temp.png`) and the Bahij font go in
`brand/carousel/` (outside git; the owner supplies them); without them the renderer draws a plain TIME KEEPER band.

## Deliver it in the studio
Publish the PNGs to the studio (`carousel/<id>/NN.png`) and write the film record with `kind: carousel`, `slides`
(their paths in order) and `caption` (`references/studio.md`). The owner sees the slides, copies the caption, saves
every PNG and the caption from the studio, and approves or asks for a change by slide number.

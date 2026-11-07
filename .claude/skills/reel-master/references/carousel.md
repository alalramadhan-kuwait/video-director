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
teaser. Only the last slide asks; its words count in the slide's 12–32. Paper ground, one
accent colour from the topic (ruby red for jewels), the TK overlay on every slide.

## The owner's rules for a carousel
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
- **Caption:** two lines in the same language, the photo credits (CC BY / BY-SA must be credited), 3–5 hashtags.

## Make it
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

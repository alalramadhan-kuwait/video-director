# The topic as a carousel (the owner's tk-topic-carousel kit)

The owner, 2 Nov 2026: «the option to generate the topic as a carousel instead of video if required… integrated into
dashboard with availability to save along with caption». A topic becomes a **Reel**, a **carousel**, or **both**
(`format:` at step 1; the studio's «ابدأ» sends it). A carousel is the written companion of a Reel: the same topic,
read in six swipes.

## What it is
A TK cover (a full-bleed photo, the TK overlay, two headline boxes bottom-right, at most 73 characters together, a
question or a surprise), then **4–5 written slides**, 1080×1350 PNGs: one idea each, a title of 2–4 words, a body of
25–32 words (the fact and one line of why or what follows; one or two key words in `<b>`, the accent colour), and one
large cut-out image that never touches the text. The layouts rotate (topImage, rightBleed, bottomImage, leftBleed,
bigCorner), never the same twice in a row; a portrait uses rightBleed or leftBleed. The order follows the Reel's arc:
problem → history or mechanism → twist → answer, the last slide ending on the viewer's question.
**A chain, not a timeline** (the owner, 2 Nov 2026, of Altivère's jewels Reel against our rubies carousel: «more
organized as flow and ideas»): the cover is a concrete puzzle the reader can see (two movements, 17 and 25 jewels:
which is better?); each slide answers the question the one before it leaves open (why jewels → the wear, in numbers →
the fix → why ruby, in numbers → but it was dear → made cheap → so how many are needed, counted out → the count became
marketing → the rule); the last slide answers the cover and hands the reader the choice. Every slide carries one
number or one mechanism the reader can check, drawn as a diagram when a photo cannot show it. A side story that does
not answer the open question (the 1705 parliament fight) is cut, however good. That question is
its own line, `ask`, set large in the accent colour under the body, and it pulls the reader in to answer (the owner,
2 Nov 2026: «دائما سؤال القارئ يكون أكبر ويشد القارئ عشان يشارك»): a real question about them or their watch, not a
teaser. Only the last slide asks; its words count in the slide's 25–32. Paper ground, one
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
- **Images:** frames of the matching Reel, the owner's own photos, or Higgsfield (credits, confirm the cost first);
  never brand press photos from the web. Each slide image is a clean cut-out
  (`var/cutenv/bin/python tools/cutout_photo.py frame.png cut.png`). The cover is a full-bleed photo.
- **A watch or a movement is shown whole** (the owner, on the rubies carousel: «محرك جزا كبير منه رايح»): the
  background remover can eat the dark parts of a movement, and a bleed layout pushes half of it off the slide. A round
  watch or movement is cut with a circle around its case (geometry, not the remover); look at the cut-out before
  rendering; a watch never takes rightBleed, leftBleed or bigCorner (they cut it), only topImage or bottomImage.
- **Caption:** two lines in the same language, the photo credits (CC BY / BY-SA must be credited), 3–5 hashtags.

## Make it
Folder `carousels/<name>/` (outside git when it holds third-party photos): `spec.json`, the images, `caption.txt`.

```json
{"language": "kuwaiti", "accent": "#a3172e",
 "cover": {"top": "ليش داخل ساعتك", "bottom": "ياقوت حقيقي؟", "image": "cover.jpg", "box": "light"},
 "slides": [{"title": "النحاس يتآكل", "body": "…", "image": "cut1.png", "layout": "topImage"},
            {"title": "لندن، 1704", "name": "Fatio de Duillier · 1664–1753", "body": "…", "image": "cut2.png"}]}
```

`python3 tools/carousel/make.py carousels/<name>` checks it, renders `out/01_cover.png … 06_slide.png` and a contact
sheet `out/sheet.jpg`: look at it (text never on the image, nothing under the top band, Arabic right to left, Latin
not reversed, the cover logo readable). The TK overlay (`Black_temp.png`, `White_temp.png`) and the Bahij font go in
`brand/carousel/` (outside git; the owner supplies them); without them the renderer draws a plain TIME KEEPER band.

## Deliver it in the studio
Publish the PNGs to the studio (`carousel/<id>/NN.png`) and write the film record with `kind: carousel`, `slides`
(their paths in order) and `caption` (`references/studio.md`). The owner sees the slides, copies the caption, saves
every PNG and the caption from the studio, and approves or asks for a change by slide number.

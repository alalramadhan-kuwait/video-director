# The post: cover, carousel, caption, credits (step 9)

## What goes to the owner with the finished film
1. **The MP4** (1080×1920, captions burned in; offer a version without captions).
2. **The caption** in the house style: a hook line, two or three short lines of the story, the closing question if the
   film has one, the music credit line (CC BY needs it), and «تابعنا…». No hashtag wall; a few relevant tags at most.
3. **The credits** (`<out>/credits.txt`, cleaned): every photo with its author, licence and page; found sounds; music;
   the voice («Voice: Jarnathan (ElevenLabs)»); AI drawings, if any, credited here only (never on screen). Remove
   local paths and duplicates; name every licence (e.g. «Licence Ouverte» for BIU Santé).
4. **The sources** list, so the owner can answer a comment.
5. **The cover** (`<out>/cover.png`): the hook's frame with the title; check it reads in the 4:5 grid crop too.

Never post, and never claim delivery of a file that was not sent.

## The Time Keeper carousel template (for a cover or a companion post)
The owner's `/post` renderer (Puppeteer → 1080×1350 PNG, 4:5) lives in their own workspace
(`timekeeper-visual/index.js`, run as `node index.js --top "…" --bottom "…" --image <file> [--image <file2>]
[--font-size N]`). When it is reachable, use it; when it is not, reproduce the template exactly:

- **Layer 1, the photo:** fills 1080×1350, `object-fit: cover`, centred.
- **Layer 2, the TK overlay PNG** on every slide: `White_temp.png` (white logo and icons) over a bright photo,
  `Black_temp.png` over a dark one; positioned `top: -25px`, stretched to 1080×1350. The choice comes from the photo's
  brightness on a 64×64 sample (luminance 0.2126R + 0.7152G + 0.0722B): bright when the logo band (x 12–88 %,
  y 7–18 %) averages ≥ 170, or its light-pixel ratio ≥ 0.35, or the edge ring ≥ 180, or the whole image ≥ 175.
- **Layer 3, the headline boxes** (cover only, when there is a title): `#headline-wrap` at right 52 px, left 52 px,
  bottom 196 px; one `.headline-box` per line, `width: fit-content`, right-aligned, padding 5px 22px 6px, 7 px apart,
  max 940 px; Bahij Helvetica Neue Bold, right to left, `line-height: 1.02`, one line each, auto-sized 32–78 px
  (a warning under 36 px: shorten the line). The box is dark (#111111, white text) only when the title zone
  (x 46–96 %, y 67–88 %) is genuinely bright (≥ 165, or ≥ 145 with a light ratio ≥ 0.45); otherwise white (#FFFFFF,
  dark text).
- Top + bottom lines together ≤ 73 characters. Slides 2+ are photo + overlay only. Every PNG is exactly 1080×1350.

For a Reel, the carousel is optional: the cover frame with the hook as the two headline lines, then two or three
detail frames (the real watch, the key number), when the owner wants a companion post.

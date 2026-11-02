# The style library: every look, and how to recommend three

## How to choose (step 6)
Read the story first. Does it need **character acting** (faces, hands, bodies), **an object or a mechanism**
(dials, movements), **numbers**, **a period**, or **a luxury feel**? Then offer exactly three styles, best first and
marked (Recommended), each with: why it fits this story, the trade-off, the tool, the cost (free or credits). Ask once
with AskUserQuestion; the owner may type any other style from this page. «Go with the recommended» = the first.
For the engine looks, show a real still of this film; for a code style, its gallery demo.

**What has worked:**
- Watch history and mechanisms (format B): the engine looks or a code style. The rubies film in the **data look**
  (the owner's pick after Altivère's jewel Reel: «The video you created is different style than the original»); 10:10
  in **Art Deco**; jewels earlier in **Copperplate Engraving**, the ruby the only coloured thing.
- People and brand stories: **paper** (Royal Oak, Panerai, Halter), with the people as paper cut-outs from their
  real photos, worlds and city zooms.
- Character-heavy parables (A, C): faces carry them, so the **AI route** first; code styles draw small, simple figures.
- Time Keeper's own brand pieces: **Wood Marquetry**.
- Pairings: movements and complications → data, exploded teardown, blueprint, microscope story; history →
  1920s newsreel, archive light table, Art Deco, copperplate engraving; numbers and studies → data, data
  physicalization; luxury → Wood Marquetry, glass product render, Art Deco; light parables → paper pop-up book,
  crayon picture book, shadow puppetry.

Whatever the style, the owner's rules hold: real photos of real watches (never drawn as a real model), captions plus
one block of text, real recorded effects only, dissolves inside an act, the house style, English digits on screen.

## A. Engine looks (free; `tools/make_film.py`, the paper-story engine)
Everything is drawn in code (DOM + headless Chromium + ffmpeg): previews in seconds, repeatable renders.

| Look | Feels | Best for | In the film file |
|---|---|---|---|
| **paper** (default) | warm paper cut-outs, layers, a slow moving camera | people and brand stories | (nothing) |
| **data** | a dark stage, big numbers, flat banners, clean photos, one ruby/gold accent | numbers, mechanisms, «what's the difference» | `look: data` (rule 18o) |
| technical drawing | pencil on light paper, labelled parts | how a part works | `technical_illustration` scenes |
| dark keynote | dark ink, big type, strong contrast | short punchy facts, launches | `dark_keynote` scenes |
| archival collage | real licensed photos and documents as prints | history with real people and watches | `archival_collage`, `archive_photo` |

**Scene templates** (`art/catalogue.yaml`; only `implemented` ones are picked; see them all drawn with
`python3 tools/motion_catalogue.py <dir> --photo <photo> [--video]`):

| Template | Shows | Main params |
|---|---|---|
| `kinetic_type` | big words rising in, an optional stamp | `lines[{text,size,at,in}]`, `stamp{text,at,color}` |
| `animated_timeline` | years on a drawn line, a card each | `events[{year,label,hero}]` |
| `map` | a moving map, pins and routes (`marker: train`) | `view`, `pins`, `routes`, `labels` |
| `city_zoom` | from the country into a city, its landmarks rising like a pop-up book | `city` (`director/studio/cities.py`), `sub` |
| `technical_illustration` | a principle drawn and labelled (crown, case, pivot in brass/worn/jewel, jewelled movement) | `kind`, `stage`, `parts`, `card` |
| `watch_movement` | a movement drawn in 3D, running, then lifting apart with names | `explode_at`, `title`, `parts` |
| `jewel_photo` | one or two real movement photos, each visible jewel ringed, then the count | `prints[{asset,aspect,marks,count,label,credit}]`, `instant` |
| `product_macro` | one product photo full frame, slow zoom | `asset`, `desc` |
| `product_reveal` | a real watch photo under a spotlight, name and year | `asset`, `name`, `year`, `credit` |
| `archive_photo` | a historical photo, full frame or a large print, a card and the credit | `asset`, `card`, `move`, `pos`, `print` |
| `archival_collage` | real photos as prints, tags | `photos[{asset,desc,aspect,at}]`, `tags` |
| `paper_cutout` | a whole watch or person cut out of its photo; a person with no whole photo drawn in paper (never a watch) | `asset`, `drawn{kind}`, `card` |
| `blueprint` | a real archive drawing (a patent) under a scanning light | `asset`, `lines`, `stamp`, `card` |
| `newspaper_card` | a front page with a stamp | `header`, `title`, `body`, `stamp` |
| `quote_card` | a quotation, who said it, where | `quote`, `who`, `source` |
| `spec_card` | specs, or two watches row by row (sourced figures) | `title`, `columns`, `rows` |
| `stat_counter` | one sourced number rolling in, landing on its spoken word | `value`, `label`, `land_on`, `source` |
| `part_of_whole` | «X of every N» | `total`, `hot`, `title`, `source` |
| `trend_chart` | a line drawing itself through sourced values | `values`, `from_label`, `to_label` |
| `compare_bars` | two to four bars, one in gold | `items[{label,value,unit,hot}]` |
| `paper_cut`, `parallax_25d` | layered paper scenery, a 2.5D push | `cliffs`, `counter`, `push` |

**Worlds** (`set:`, `director/studio/sets.py`, drawn in code with their ambience): `underwater`, `sea_night`,
`florence`, `workshop`, `radium`, `archive`, `auction_room`, `paris_rail`, `home_70s`, `home_70s_driver`,
`paris_atelier`, `jura`, `basel_fair`, `swiss_atelier`, `waiting_years`. **Moods** (`mood:`): mystery, fear, sadness,
tension, joy, wonder. **Backdrops:** `photo: <slot>` puts a related photo, dimmed, behind a scene of words.
Themes: `tk-bone`, `tk-ink`, `tk-black`, `tk-graphite`; Time Keeper boxes are #111111 / #FFFFFF. Every film ends on
the Time Keeper end card. Keep content between y≈380 and y≈980 of the 720×1280 frame (banner above, captions below).

## B. The 66 code-film styles (free; lemo-opuscar, MIT; build: `code-styles.md`)
Gallery of every demo: https://lemomo-ai.github.io/lemo-opuscar/
- **Edit & Documentary:** Caption News (caption-news), 1920s Newsreel (newsreel), Live Countdown Split-screen
  (countdown), Time-lapse Symphony (city-symphony), Visual Investigation (visual-investigation), Constructivist
  Montage (kino-montage), Sports Telestrator (telestrator), Broadcast News Package (news-package)
- **Evidence films:** Satellite Briefing (satellite-briefing), Engineering Briefing Board (briefing-board), LiDAR
  Survey (lidar-survey), Projection on White Model (white-model), Data Physicalization (data-physical), Exploded
  Teardown (teardown), Microscope Story (microscope), Archive Light Table (archive-lighttable)
- **Hand-drawn & painting:** Crayon Picture Book (crayon-book), Watercolor Brush (watercolor), Chinese Ink Wash
  (ink-wash), Impasto Oil Painting (impasto), One-line Drawing (one-line), Whiteboard Explainer (whiteboard), Urban
  Sketch · Pen & Wash (urban-sketch), Chalkboard (chalkboard)
- **East Asian traditions:** Shadow Puppetry (shadow-puppet), Ukiyo-e (ukiyoe), Red Paper-cut (papercut-red),
  Paper-cut Lightbox (paper-lantern)
- **Print & printmaking:** Risograph Print (risograph), Halftone Dossier (halftone-dossier), Woodcut Print (woodcut),
  Copperplate Engraving (engraving), Silkscreen Travel Poster (silkscreen-poster), Printed Long Take
  (printed-long-take)
- **Graphic & type:** Swiss Motion Graphics (swiss-motion), 60s Spy Title Sequence (spy-titles), Art Deco (art-deco),
  Blueprint (blueprint), Stained Glass (stained-glass), Pictogram Motion (pictogram-motion), ASCII / CRT Terminal
  (ascii-crt)
- **Information & keynote:** Data Storytelling (dataviz), Isometric Infographic (iso-infographic), Dark Tech Keynote
  (dark-keynote), Living Screencast (living-screencast), Sci-fi Hologram HUD (hologram-hud), Transit Map
  (transit-map), Isometric Picture Book (isometric-picture-book), Circuit Board (circuit-board)
- **Cartoon & anime:** 1930s Rubber Hose (rubber-hose), 80s Cel Anime (cel-anime-80s), Sci-Fi Sitcom Toon
  (scifi-toon), Mid-century Cartoon (midcentury-toon)
- **Games:** 16-bit Pixel RPG (pixel-rpg), HD-2D (hd-2d), Microgame Frenzy (microgame), Game Show Flat (game-show)
- **Cinema & eras:** 1920s Silent Film (silent-film), Liminal Found Footage (backrooms)
- **Materials & 3D:** Brick Toy (brick-toy), Paper Pop-up Book (paper-popup), Tilt-Shift Miniature (tilt-shift),
  Low-poly Isometric Island (lowpoly-island), Glass Product Render (glass-product), Memphis Diorama
  (memphis-diorama), Desktop Flythrough (desktop-flythrough)

Trade-offs: 3D styles (tilt-shift, glass-product, lowpoly-island) render slowly here (software WebGL); human figures
built from coordinates stay simple, so emotion moves to hands and objects; library demos are 16:9 and must be
re-laid for 9:16, not cropped.

## C. Wood Marquetry (free; Time Keeper's own signature style; `wood-marquetry.md`)
Every colour and shadow a cut veneer leaf with real grain, Patek-level fineness, rigid motion only. Best for brand
pieces and luxury; slow and simple; faces plateau around 3.5–4 / 5 against the reference art.

## D. AI route (Higgsfield; uses credits; only with an explicit yes)
Clay / claymation 3D (the Clayrified look), stylized 3D animation, cinematic realistic. For character-heavy parables
where faces carry the emotion. Real watches are never generated: their real photos are composited. Confirm the
credit cost first (`story-engine.md` §7 for the prompts).

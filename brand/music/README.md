# Music library

**The whole catalogue** — `incompetech.json` lists every Kevin MacLeod track on incompetech.com (1,443: title, length,
feel, instruments, tempo). Licence CC BY 4.0: commercial use allowed with the credit
(evidence: https://incompetech.com/music/royalty-free/licenses/). Only the list is kept here; a film downloads the one
track it uses into `~/.cache/video-director/music/`, with its licence record (source, licence, credit, date, sha256).

**How a film gets its track** — by the brand's mood in `brand/timekeeper.json` (`music`: prefer / avoid feels,
instruments, words to avoid, max tempo) and the film's length; one of the ten best, picked by the film, so films differ.
The credit line goes in the post caption with the film.

```bash
python3 tools/music.py pick --seconds 150 --seed <film>     # the track a film gets
python3 tools/music.py search calm piano --seconds 150      # what fits the brand
python3 tools/music.py get "Gymnopedie No. 1" --save DIR    # a named track
```

**The owner's own track** wins over the catalogue: put it here (mp3, m4a, wav) with its licence record beside it,
same name — `calm-cinematic.mp3` + `calm-cinematic.licence.json`:
```json
{ "licence": "Pixabay Content License", "source": "https://pixabay.com/music/…", "commercial_use": true, "attribution": "" }
```
A track without a record, or marked non-commercial, is never used. No network and nothing cached: the film has no music.

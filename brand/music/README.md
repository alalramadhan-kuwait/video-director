# Music library

Put a commercially licensed track here (mp3, m4a, wav) and, beside it, its licence record with the same name:

`calm-cinematic.mp3` + `calm-cinematic.licence.json`
```json
{ "licence": "Pixabay Content License (commercial use, no attribution)", "source": "https://pixabay.com/music/…", "commercial_use": true, "bought_or_downloaded": "2026-10-22" }
```
The film uses the first track that has a licence record, at the brand's music level (`gain_db` in `brand/timekeeper.json`,
quietly under the voice). A track without a record is never used. No track: the film has no music.

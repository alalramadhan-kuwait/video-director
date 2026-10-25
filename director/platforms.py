"""Where the film is posted decides how it is delivered: its length, one file or parts, a separate cover, and where the
app's own buttons cover the picture. Learned from video-ad-editor (references/platforms.md, v3.11); its figures come
from published guides (October 2026), not the platforms' own pages, so the safest value is kept.

The platform is the film file's `platform:`, else the brand's `export.platform`. Every film here is vertical (9:16);
a landscape YouTube video would need its own layout and is not offered.

Zones are in 1080x1920 pixels: no words inside a hard zone (the app's name and follow button on top, the caption, sound
and account below, like / comment / share on the right); the caution band is reported but does not fail.
`caption_y` is where the caption row starts (720x1280 storyboard pixels): TikTok covers more of the bottom, so its
captions sit higher.
"""
from __future__ import annotations

PLATFORMS = {
    'reels': {
        'name': 'Instagram Reels', 'max_seconds': 180, 'parts': False, 'cover': True, 'caption_y': 1004,
        'note': 'up to 3 minutes is sure for every account; reach drops after that',
        'zones': [{'k': 'top (account name, follow)', 'x': 0, 'y': 0, 'w': 1080, 'h': 150, 'hard': True},
                  {'k': 'bottom (caption, sound, account)', 'x': 0, 'y': 1620, 'w': 1080, 'h': 300, 'hard': True},
                  {'k': 'bottom caution band', 'x': 0, 'y': 1500, 'w': 1080, 'h': 120, 'hard': False},
                  {'k': 'right (like, comment, share)', 'x': 950, 'y': 1100, 'w': 130, 'h': 650, 'hard': True}]},
    'tiktok': {
        'name': 'TikTok', 'max_seconds': 600, 'parts': False, 'cover': True, 'caption_y': 968,
        'note': 'one video per episode; 1-3 minutes works best for a series',
        'zones': [{'k': 'top (tabs, search)', 'x': 0, 'y': 0, 'w': 1080, 'h': 150, 'hard': True},
                  {'k': 'bottom (caption, sound, account)', 'x': 0, 'y': 1560, 'w': 1080, 'h': 360, 'hard': True},
                  {'k': 'right (like, comment, share)', 'x': 940, 'y': 850, 'w': 140, 'h': 900, 'hard': True}]},
    'shorts': {
        'name': 'YouTube Shorts', 'max_seconds': 180, 'parts': False, 'cover': False, 'caption_y': 980,
        'note': 'over 3 minutes it is not a Short; the cover is picked from a frame in the app',
        'zones': [{'k': 'top (search, menu)', 'x': 0, 'y': 0, 'w': 1080, 'h': 150, 'hard': True},
                  {'k': 'bottom (title, channel)', 'x': 0, 'y': 1580, 'w': 1080, 'h': 340, 'hard': True},
                  {'k': 'right (like, comment, share)', 'x': 950, 'y': 1100, 'w': 130, 'h': 650, 'hard': True}]},
    'whatsapp': {
        'name': 'WhatsApp', 'max_seconds': None, 'parts': True, 'cover': False, 'caption_y': 1004, 'part_seconds': 85, 'part_mb': 16,
        'note': 'a chat takes files under 16 MB: the film goes in parts of at most 85 s, cut between scenes',
        'zones': []},
}
ALIASES = {'instagram-reels': 'reels', 'instagram': 'reels', 'ig': 'reels', 'youtube-shorts': 'shorts', 'youtube': 'shorts',
           'wa': 'whatsapp'}


def get(name: str | None) -> tuple[str, dict]:
    """(id, settings) of a platform by its id or a common name; Reels when none is given (the brand's default)."""
    key = ALIASES.get((name or 'reels').strip().lower(), (name or 'reels').strip().lower())
    if key not in PLATFORMS:
        raise ValueError(f'unknown platform {name!r}: one of {", ".join(PLATFORMS)}')
    return key, PLATFORMS[key]


def of(film: dict, brand_cfg: dict) -> tuple[str, dict]:
    return get(film.get('platform') or (brand_cfg.get('export') or {}).get('platform'))


def zones(platform: dict, width: int = 720) -> list[dict]:
    """The platform's zones in storyboard pixels (the films are drawn at 720x1280 and rendered at 1.5x)."""
    k = width / 1080
    return [{**z, **{c: round(z[c] * k, 1) for c in ('x', 'y', 'w', 'h')}} for z in platform['zones']]


def length_warning(platform: dict, seconds: float) -> str | None:
    cap = platform.get('max_seconds')
    if cap and seconds > cap:
        return f"{seconds:.0f} s is longer than {platform['name']} allows for sure ({cap} s): {platform['note']}"
    return None


def parts(starts: list[float], durs: list[float], limit: float) -> list[tuple[float, float]]:
    """The film cut into parts of at most `limit` seconds, each cut at the start of a scene (never inside a line).
    A single scene longer than the limit becomes a part of its own."""
    out, a = [], 0.0
    end = starts[-1] + durs[-1]
    for s, d in zip(starts, durs):
        if s + d - a > limit and s > a:
            out.append((a, s)); a = s
    out.append((a, end))
    return [(round(x, 2), round(y, 2)) for x, y in out]

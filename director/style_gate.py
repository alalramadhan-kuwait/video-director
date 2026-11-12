"""The style gate, as a check a tool can run: no build without the owner's style pick (the owner, 10 Nov 2026: «The
style stage was skipped… You marked الأسلوب ✓ and built «فيديو v1» without showing me the style card»).

`tools/studio_gate.py` reads a film's studio record and refuses a build or a render unless the record shows his pick,
in one of two ways:

1. his tap on the page: `style_pick {by: 'owner', choice, …}`, which only the page writes
   (references/studio.md, «The style gate»);
2. his pick in chat: `flow.choice` set, `flow.stage == 'done'`, and the film-level
   `style_pick_chat {at, words}` that the back end writes when he picks in chat (`words`: his own words, `at`: the
   real UTC time). A line in `changes` is not a pick: anyone can write one.

`problems()` lists why a record is refused; an empty list opens the build."""
from __future__ import annotations


def _text(v) -> str:
    return v.strip() if isinstance(v, str) else ''


def record(doc) -> dict | None:
    """The film record itself: as given, or under `data` when the row was passed whole."""
    if not isinstance(doc, dict): return None
    if not any(k in doc for k in ('flow', 'style_pick', 'style_pick_chat')) and isinstance(doc.get('data'), dict): return doc['data']
    return doc


def picked_on_page(film: dict) -> bool:
    p = film.get('style_pick')
    return isinstance(p, dict) and p.get('by') == 'owner' and bool(_text(p.get('choice')))


def chat_problems(film: dict) -> list[str]:
    """What is missing for a pick made in chat to count."""
    flow, chat, out = film.get('flow'), film.get('style_pick_chat'), []
    flow = flow if isinstance(flow, dict) else {}
    if not _text(flow.get('choice')): out.append('`flow.choice` is empty')
    if flow.get('stage') != 'done': out.append(f"`flow.stage` is {flow.get('stage')!r}, not 'done'")
    if not isinstance(chat, dict): out.append('no `style_pick_chat {at, words}`')
    else:
        if not _text(chat.get('words')): out.append('`style_pick_chat.words` (his own words) is empty')
        if not _text(chat.get('at')): out.append('`style_pick_chat.at` (when he said it, UTC) is empty')
    return out


def problems(doc) -> list[str]:
    """Why this film may not be built yet; empty when the owner's pick is on the record."""
    film = record(doc)
    if film is None: return ['not a film record (a JSON object is needed)']
    if picked_on_page(film): return []
    chat = chat_problems(film)
    if not chat: return []
    p = film.get('style_pick')
    if isinstance(p, dict) and p.get('by') != 'owner': page = f"`style_pick.by` is {p.get('by')!r}, not 'owner'"
    elif isinstance(p, dict): page = '`style_pick.choice` is empty'
    else: page = 'no `style_pick` from the page'
    return [f'no style pick from the owner: {page}; and no pick in chat on the record ({"; ".join(chat)})',
            'show him the style card and wait for his pick; nothing is built or rendered before it']

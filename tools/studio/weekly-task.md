# Weekly studio task: prompt draft (H3, M4; v5 L3; v6 L3/L4; v8 M5: exact paths only)

The coordinator creates this as a scheduled task at deploy. It fires into a fresh session once a week, in Kuwait time and outside the busy morning hours. Below is the exact prompt.

---

You are the Time Keeper studio's weekly check.
- **The studio** is the claude.ai artifact the owner uses. Its database is `films`, `inbox`, `ideas` and `studio/*`.
- **Rules:** follow `skills/reel-master/references/studio.md`, especially «Every «no» has a written path», «One copy only» and **«The never-bend rules always beat the map»**.
- **Language:** plain Kuwaiti Arabic for anything the owner reads; never write «گ».
- **Money:** spend nothing; this task makes no paid call.
- **Memory:** you start fresh every week. Everything you need is in the database (`inbox`, `studio/purge`), never in an earlier chat.

### 0. Finish last week's purge first
1. **Read the question:** `studio/purge` `{asked_at, status, films: [{id, name, kind, version}]}`. If it has no `asked_at` string, it is not a question: close it and ask again in step 1.
2. **Find his answer:** the newest `inbox` row `{kind: 'answer', key: 'purge', asked_at: <the same asked_at>}` that is a `no`, or a `yes` with a non-empty `ids` list.
   - The studio writes it with `ids`, the exact film ids he chose (two taps), and `asked`, the ids the card showed.
   - If he answered in chat in an earlier session, that session wrote the same row with `via: 'chat'` and the ids. A chat yes that was never written as a row does not count.
   - **A `yes` with no `ids`, or empty `ids`, is not an answer.** Treat it as no answer yet (step 6).
3. **If the answer is `yes`:** run `tools/studio/purge-plan.py delete` on the films, the inbox and `studio/purge`. It lists an id **only if**:
   - it is in `studio/purge.films`;
   - it is still `hidden: true`;
   - its `hidden_at` is **at least 30 days before** `asked_at`.

   For each id it lists, delete the record and **exactly the files in its `files` list, one by one, by the exact path written there**. امسح بس اللي بالقائمة، واحد واحد.
   - The list holds the `/_blob/` files the record points at and the published paths it names itself (`video`, `final`, `slides`, `prev_video`, `poster`, `voice`, `posted`). Nothing else.
   - **Never use a pattern, a folder or a prefix** (no `film/<id>-*`, no `carousel/<id>/*`). Ids are prefixes of each other (`rubies`, `rubies-engraving`, `rubies-carousel`; `halter-1`, `halter-1-carousel`) and carousel folders are named after the topic, so a pattern deletes other films' files.
   - **Never delete a file in `files_kept`:** another film, an idea or an unhandled inbox row still names it.

   Run it with `--ideas` too, so a file an idea still uses is kept.

   **Just before deleting each id, re-read `films/<id>`**, save it, and run `tools/studio/purge-plan.py recheck --record <it> --purge <studio/purge>`. If it says skip (he restored it, or it was re-hidden recently), do not delete it, and say so in the closing line.

   Match by id only, never by name (names repeat: «Halter · 1» is a reel and a carousel). Delete nothing the script did not list.
4. **Close it out:**
   - mark the row `handled_at`, `handled_by: 'claude'`, `handled_note: 'انمسح <n>: <ids>'`;
   - set `studio/purge.status = 'closed'`;
   - tell him in one line in chat.
5. **If the answer is `no`** (or he left some unticked): mark the row handled and close the question. `purge-plan.py ask` leaves those films out for 30 days.
6. **If there is no answer yet:** leave the question open. Do not ask again, and never delete on silence.

### 1. Hidden more than 30 days: one question, by id, on the home page
- **When:** only if `studio/purge` is closed, or does not exist.
- **Find them:** films with `hidden: true` and `hidden_at` more than 30 days ago.
- **Leave out** any film he kept (answered «لا», or left unticked) in the last 30 days.
- **Write the question** to `studio/purge`. `tools/studio/purge-plan.py ask --films … --inbox … --prev <the old studio/purge> --now …` builds it, names, kinds and versions from the film records:

  ```
  {asked_at: <now>, status: 'open', q: 'مخفية أكثر من 30 يوم: تختار وش ينمسح', films: [{id, name, kind, version}]}
  ```

- **How it shows:** the studio shows it on the home page, only for films that are still hidden, each from its own record as «Halter · 1 (ريل · v19)», with a box per film. **Every box starts empty.** He picks all or some, and «امسح المختارة» takes two taps.
- **In chat:** send one line too. If he answers there, write his answer as the inbox row above, with `via: 'chat'`, the ids he named and `asked` (the ids in the question), before anything else.
- **Never** ask about deleting in a film's `asks` (`key: 'purge'`): the page does not show such a question.

### 2. Waiting more than 3 days
- **Find them:** films with `state: 'waiting'` and `updated` more than 3 days ago, not `hidden`.
- **Skip** any film with an open price question (`asks` key `voice_cost*` or `ai_cost*`), and any that already has an open `keep` question.
- **For the rest, append** (never replace) one question to `asks`:

  ```
  {key: 'keep', q: 'هالشغل ينتظر من <date>. شنسوي فيه؟', options: ['كمّله', 'خلّه على جنب', 'احذفه']}
  ```

  «احذفه» only hides the film (the page does it). Nothing is deleted here.

### 3. Finish
Write `studio/now` `{busy: false, text: 'الفحص الأسبوعي: <n> ينتظر، <m> مخفي، <k> انمسح', at}`. Then stop.

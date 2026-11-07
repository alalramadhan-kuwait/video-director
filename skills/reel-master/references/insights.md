# After posting: reading Instagram's numbers and building the recipe

The owner, 3 Nov 2026: «حط اوبشن تم النشر وتنطر التحليل بعد مدة معينه انت تحددها. ادز لك صور للتحاليل من
انستقرام وتعرف مستوى الريل اذا كانت ارقامه ناجحه ولا لا ونحاول نحسن لين نوصل حق افضل وصفه للخوارزمية مع بحثك
اليومي للنصائح». This file is how a posted Reel or carousel is read, judged and turned into the recipe.

## The flow
1. **«تم النشر ✓»** in the studio (on a finished film or an approved carousel) sets `state: posted`,
   `posted: {at, version}`, and tells Claude (inbox + comment).
2. **Two reads**, chosen by Claude:
   - **48 hours** (`48h`, «أول قراءة»): Instagram decides most of a Reel's reach in its first two days. This read
     shows the hook (skip rate), the watch time, and whether the Reel went past the followers.
   - **7 days** (`7d`, «القراءة النهائية»): the settled numbers: the reach, shares, saves and follows.
3. When a read is due, the numbers come straight from Instagram through Supabase (`studio_page()`, cached in
   `studio/ig`). Only when that sync is down does the film wait for screenshots («بانتظارك · صور الإحصائيات»), which
   he uploads in the studio (`insights_shots`) or sends in the chat (`insights_sent`).
4. Claude reads them, writes the verdict on the film (`insights`), updates the recipe (`studio/recipe`), and adds a
   row to the log below.

## What to read from the screenshots
The studio asks for four screens (the Reel → View insights): the overview, the watch time, the retention graph, and
the interactions. Write these into `insights[].numbers` (Arabic names, English digits):

| Name | What it is | Why it matters |
|---|---|---|
| المشاهدات | Views | the size |
| الوصول | Accounts reached | the people, not the replays |
| غير المتابعين | % of views from non-followers | the algorithm recommended it (Explore, the Reels tab) |
| معدل المشاهدة | average watch time, and as a % of the film's length | Mosseri's first signal |
| Skip rate | % who swiped away in the first seconds (in Insights since 2026) | the hook |
| المشاركات/الوصول | shares (DM sends) ÷ reach × 100 | Mosseri: the strongest signal for reach beyond followers |
| الحفظ | saves | the value of the facts |
| اللايكات/الوصول | likes ÷ reach × 100 | Mosseri: weighs most with followers |
| المتابعين الجدد | follows from this Reel | the account's growth |

**The retention graph:** find the second where the curve drops hardest. Map it to the film's line at that second
(`plan.json`, the caption chunks, or the film file's line timings), and say what was on screen and in the voice.
That is the lesson with the most use.

Instagram's ranking signals (Adam Mosseri, January 2025, restated since): watch time, likes per reach and sends
per reach. Likes weigh more with followers, and sends more with non-followers. Instagram does not publish numeric
weights; treat a blog's «sends are 3–5× likes» as a claim, not a fact.

## The verdict: against our own posts
General benchmarks vary too much between sources to judge a Reel (engagement «averages» run from 0.3% to 2.5%
depending on who counts and how). So the baseline is **the median of our own earlier posts at the same read** (from
the log below), of the same format (Reel or carousel):
- **ناجح (`good`)**: views at least 1.5× the baseline, with watch time % and shares/reach not below it; or watch time %
  and shares/reach both clearly above it.
- **ضعيف (`bad`)**: views under 0.6× the baseline, and the skip rate above it.
- **متوسط (`mid`)**: anything else.
- With fewer than three earlier posts of the format, write the numbers, say «أول قراءات، نقارن بالجاية», and judge
  only what stands out on its own (a skip rate over half the viewers, or a retention cliff).

`vs` is one sentence against the baseline («المشاهدات ضعف معدّلنا، والمشاركات نفس المعدّل»).

## Lessons, next, and the recipe
- `lessons`: what this film shows, each tied to a choice we made (the hook line and first frame, the length, the act
  where people left, the cover, the caption's first line, the posting hour). At most four.
- `next`: one or two concrete changes for the next film.
- **The recipe** (`studio/recipe` {updated, items: [{rule, why, from}]}): a rule joins it when two posts show it, or
  one clear comparison between two versions of the same idea. `why` gives the numbers, `from` the films. A rule that
  later posts contradict is reworded or removed, and the change is logged. Étienne's daily tips may suggest what to
  test; they never write the recipe.
- Never put the owner's screenshots in git (the repository is public). The numbers in the log are the account's own
  results and may stay.

## Log
| Date | Film | Format | Read | Views | Non-followers | Watch time | Skip | Shares/reach | Saves | Follows | Verdict | Lesson |
|---|---|---|---|---|---|---|---|---|---|---|---|---|

# director.qa — read-only adapters around the production checkers

These adapters run the real production checkers and turn what they print into findings. They contain no checking
logic of their own: a finding is always a line the checker printed, or a note that the run itself went wrong.

| adapter | runs | default location (override) |
|---|---|---|
| `paper_story.check(storyboard_json, out_dir=None, timeout=600)` | `node render.mjs <copy>/<story>.json --check` | paper-story skill in the audit clone (`VD_PAPER_STORY_RENDER`) |
| `safe_zone.check(workdir, platform=None, shot=True, out_dir=None, timeout=600)` | `node 08_safe_check.js <copy> [--shot]` | `/home/user/majedphotos/video-ad-editor/video-ad-editor` (`VD_VAE_ROOT`) |

Both also take `tool_path=` and `tmp_root=` (where the scratch copy goes). Both return
`{tool, tool_path, tool_sha256, input, exit_code, passed, findings, summary, raw_stdout, raw_stderr, ran_on_copy, network_blocked, seconds}`.
A finding is `{code, severity, scene, from, to, detail, raw, data?}`. `tool_sha256` is the checker's own hash, so a
later change in the production tool shows up. With `out_dir` the result is also saved there as JSON.

## How each runs

1. The input is copied to a fresh temp dir: the storyboard's folder (plus any relative asset path that climbs out of it,
   copied to the same relative place), or the whole workdir. Files of 64 MB or more are symlinked, not copied (the
   checkers only read them). `.git`, `node_modules` and `__pycache__` are left out.
2. `safe_zone` only: `platform` is merged into the **copy's** `safe.json`, and any old `safe.jpg` is removed from the copy.
3. The checker runs with `node`, with `ELEVENLABS_API_KEY`, `FAL_KEY` and `PM_DEBUG` removed, every proxy variable
   pointed at a dead local port (Chromium and npm then cannot reach the network), and `npm_config_offline=true`.
   paper-story gets `NODE_PATH` set to an existing playwright-core (read-only); if none is found the adapter refuses
   to run rather than let `render.mjs` npm-install one. The safe-zone checker gets `CHROME_PATH` set to the Chromium in
   `/opt/pw-browsers`, because it looks for Chrome before it does anything else, even on the hook-only path.
4. stdout and stderr are parsed line by line. A line the adapter does not recognise is kept as `UNPARSED` (info).
5. `safe_zone` only: a `safe.jpg` the checker wrote into the copy is copied to `out_dir/safe.jpg`. Its printed path is
   rewritten to that file. The temp copy is then deleted.

## What they never do

They never write, move or delete anything in a production tool, its project or the original input. They never run a
checker on an original workdir, because `08_safe_check.js --shot` writes `<workdir>/safe.jpg`. They never run
`npm install` or `playwright install`, make network calls, or use API keys.

## Exit codes and codes

| checker | exit | result |
|---|---|---|
| render.mjs --check | 0 | `passed` true |
| | 1 + findings | `passed` false |
| | 1 + `render: …` on stderr (it dies with 1 too) | `TOOL_ERROR`, `passed` false |
| | anything else, or timeout | `TOOL_ERROR` |
| 08_safe_check.js | 0 | `passed` true |
| | 3 | `passed` false (late hook or a hard zone) |
| | anything else (1 = uncaught exception), or timeout | `TOOL_ERROR` |

The paper-story codes are `FACE_COVERED`, `UNDER_BANNER`, `CUT_BY_FRAME`, `OVERLAP` and `ON_CAPTIONS` (major),
`SOFT_IMAGE`, `PLACEHOLDER` and `TOOL_WARNING` (minor), and `PAGE_ERROR` (major). `scene` is the checker's
1-based scene number, and `data.scene_id` is the storyboard's `id`.

The safe-zone codes are `ZONE_HARD` (critical), `HOOK_LATE` (major), `ZONE_SOFT` (minor), `UNKNOWN_PLATFORM` (major)
and `COMPOSE_ERROR` (major). Three are info: `NO_PIXEL_CHECK` means there is no `compose.html`, so only the hook was
checked. `OFFLINE_RESOURCE` means a web font was blocked, so text was measured with the fallback font. The last is
`UNPARSED`. Both adapters also emit `TOOL_ERROR` (critical) and `PARSE_MISMATCH` (major). `PARSE_MISMATCH` means the
checker's own totals or exit code disagree with what was parsed, which usually means its output format changed.

## Known limits

- paper-story: `.banner` in `engine/paper.css` is `width:0;height:0`, so the checker's banner rectangle is empty and it
  never reports "under the banner" or "the banner covers a head". The adapter parses those lines, but the production
  checker cannot currently print them. See the expected-failure test.
- safe-zone: offline runs measure text in the fallback font when the theme font comes from Google Fonts. Compare a
  borderline result with an online run of the production tool before you act on it.
- Chromium fails to start when `TMPDIR` is a long path, so `TMPDIR` is only moved into the scratch dir when that path
  is short. Otherwise Chromium's own profile goes to the system temp dir, as it does in production.

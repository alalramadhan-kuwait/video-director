# Studio deploy and upkeep tools

Moved from staging on 9 Nov 2026 (the owner: «انقل السكربتات للريبو وسوّ المهمة الأسبوعية») so a session that has only this repo can run them.

- `purge-plan.py`: the weekly purge, by id (`ask`, `delete`, `recheck`). The weekly task runs it; see `weekly-task.md` and `tests/test_studio_purge.py`.
- `backfill.py`, `reupload.py`, `check-version.py`: release steps for the studio page (approvals bound to `/_blob/` addresses; re-uploads that keep posted films bound). Dry-run by default; they write a batch file, never the database.
- `flow-migrate.js`: moves a saved workflow map to a new page build.
- `RELEASE-CHECKLIST.md`: the order of a studio release (the v11 go-live log is in the session record).

All of them read local JSON copies of the studio's `films`, `inbox`, `ideas` and `studio/*` and only write files.

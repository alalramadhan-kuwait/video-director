"""Read-only QA adapters around the production checkers.

Each adapter CALLS an existing production checker as a subprocess (`node <script> ...`), on a fresh temporary copy of
the input, with paid-API keys removed and the network blocked, and turns the checker's own stdout and exit code into
structured findings. No checking logic is reimplemented here, and nothing in the production tools or their projects is
ever written to.

    paper_story.check(storyboard_json)   -> paper-story `render.mjs --check`   (faces covered, cut by frame, ...)
    safe_zone.check(workdir)             -> video-ad-editor `08_safe_check.js` (hook timing, platform safe zones)

Every result carries the checker's sha256, so a later change in the production tool is visible.
"""

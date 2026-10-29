# Time Keeper Studio (web app)

The owner's film studio as an app for the phone: the stages on a watch dial, what Claude is doing now, the voices and the
latest cut. It installs from Safari (Share, Add to Home Screen) and is served by GitHub Pages (`.github/workflows/studio-app.yml`).

- **Its server** is the `studio` Edge Function in the Time Keeper Supabase project (code in `timekeeper-online/supabase/
  functions/studio`), in the `studio` schema and the private `studio-media` bucket, apart from the shop's data.
- **Signing in:** the first time, with the one-time code Claude gives; the owner then picks a passcode. No Supabase auth user
  is made, so nothing appears in the staff app. Five wrong tries lock sign-in for 15 minutes.
- **Claude's side:** `tools/studio_api.py` (write a document, post a step, upload media, read the owner's taps). Claude's key
  lives outside the repository.
- The page is built from the claude.ai studio page; change `index.html` here directly from now on.

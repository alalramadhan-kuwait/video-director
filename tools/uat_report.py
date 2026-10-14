"""Build the UAT report (one self-contained HTML file with screenshots embedded) and the deliverable files.

    PYTHONPATH=. python3 tools/uat_report.py OUT_DIR
Inputs: var/uat/results.json, var/uat/shots/*.png, var/uat/defects/defects.json, var/uat/defects.log,
        uat/classification.json (the verdict per feature, written by hand from the evidence), var/audit/AUDIT_REPORT.md,
        the project's state from the UAT server copy (var/dashboard-uat).
"""
import base64, html, json, os, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
os.environ.setdefault('VD_DASHBOARD_VAR', str(ROOT / 'var/dashboard-uat'))
from director.studio import api  # noqa: E402

UAT = ROOT / 'var/uat'
PID = (UAT / 'pid').read_text().strip()
V = api.view(ROOT / 'var/dashboard-uat', PID)
S = api.studio(ROOT / 'var/dashboard-uat')
R = json.loads((UAT / 'results.json').read_text(encoding='utf-8'))
for r in R: r['rerun'] = False                             # one fresh run: nothing is re-run inside it
D4 = ROOT / 'var/uat-d4/results.json'                       # the seek test runs on a disposable copy (it switches the hook)
if D4.exists():
    for r in json.loads(D4.read_text(encoding='utf-8')):
        if r['stage'] != 'page': R.append({**r, 'name': r['name'] + ' (disposable copy)', 'rerun': False})
SH_D4 = ROOT / 'var/uat-d4/shots'
NOTES = json.loads((UAT / 'harness_notes.json').read_text(encoding='utf-8')) if (UAT / 'harness_notes.json').exists() else {}
for r in R:
    if not r['pass'] and r['name'] in NOTES: r['note'] = NOTES[r['name']]
PRIOR = {n: json.loads((UAT / f'results-{n}.json').read_text(encoding='utf-8')) for n in ('run1', 'run2', 'run3') if (UAT / f'results-{n}.json').exists()}
DEF = json.loads((UAT / 'defects/defects.json').read_text(encoding='utf-8')) if (UAT / 'defects/defects.json').exists() else None
CLS = json.loads((ROOT / 'uat/classification.json').read_text(encoding='utf-8'))
AUDIT = (ROOT / 'var/audit/AUDIT_REPORT.md').read_text(encoding='utf-8') if (ROOT / 'var/audit/AUDIT_REPORT.md').exists() else '(not yet)'
FIXED = [l[2:] for l in (UAT / 'defects.log').read_text(encoding='utf-8').splitlines() if l.startswith('- ')]
E = html.escape


def img(name, w=300, cap=''):
    p = UAT / 'shots' / f'{name}.png'
    if not p.exists(): p = SH_D4 / f'{name}.png'
    if not p.exists(): return f'<p class="miss">missing screenshot {E(name)}</p>'
    j = OUT / '_tmp.jpg'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(p), '-vf', f"scale='min({w * 2},iw)':-2", '-q:v', '5', str(j)], check=True)
    b = base64.b64encode(j.read_bytes()).decode(); j.unlink()
    return f'<figure><img src="data:image/jpeg;base64,{b}" alt="{E(name)}" loading="lazy"><figcaption>{E(cap or name)}</figcaption></figure>'


def fileimg(path, w=360, cap=''):
    j = OUT / '_tmp.jpg'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(path), '-vf', f"scale='min({w * 2},iw)':-2", '-q:v', '5', str(j)], check=True)
    b = base64.b64encode(j.read_bytes()).decode(); j.unlink()
    return f'<figure><img src="data:image/jpeg;base64,{b}" alt="{E(cap)}" loading="lazy"><figcaption>{E(cap)}</figcaption></figure>'


def res_rows(stage):
    rows = [r for r in R if r['stage'] == stage]
    return ''.join(f'<tr><td class="{"ok" if r["pass"] else "bad"}">{"PASS" if r["pass"] else "FAIL"}</td><td>{E(r["name"])}{" <i class=muted>(re-run after the fix)</i>" if r["rerun"] else ""}</td><td class="det">{E(r["detail"][:260])}{"<br><b>Note:</b> " + E(r["note"]) if r.get("note") else ""}</td></tr>' for r in rows)


VERDICT = {'PASS': 'ok', 'PASS (MOCK)': 'unk', 'FAIL': 'bad', 'PARTIAL': 'wait', 'BLOCKED': 'blk', 'NOT TESTED': 'unk'}
# ------------------------------------------------------------------ deliverables
latest = V['latest_render']
film = S.path(PID, latest['file']) if latest else None
deliver = {}
if film:
    share = OUT / 'rolex-oyster-DRAFT.mp4'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(film), '-vf', 'scale=720:-2', '-c:v', 'libx264', '-preset', 'slow', '-crf', '26',
                    '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', str(share)], check=True)
    deliver['film'] = share.name
    sheet = OUT / 'draft-contact-sheet.jpg'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(film), '-vf', 'fps=1/4,scale=200:-2,tile=8x5:padding=4:color=0x202020', '-frames:v', '1', str(sheet)], check=True)
    deliver['sheet'] = sheet.name
lines = V['script_latest']['lines']
(OUT / 'rolex-oyster-script.md').write_text('# Rolex Oyster — narration script (approved v%d)\n\n' % V['scripts'][-1]['v'] +
    '\n'.join(f'{l["id"]}. {l["text"]}' for l in lines) + '\n\nSources: research/rolex-oyster.json (claims c1–c10).\n', encoding='utf-8')
sb = V.get('storyboard') or {'scenes': []}
(OUT / 'rolex-oyster-storyboard.csv').write_text('scene,start_s,duration_s,technique,art,voice,banner,line\n' + '\n'.join(
    f'{s["id"]},{s["start"]},{s["dur"]},{s["technique"]},{s["status"]["art"]},{s["status"]["voice"]},"{s["banner"] or ""}","{s["line"]}"' for s in sb['scenes']), encoding='utf-8')

# ------------------------------------------------------------------ html
CSS = """
:root{--bg:#f4f4f2;--panel:#fff;--ink:#16181c;--muted:#5d636c;--line:#dcdcd6;--ok:#1d7a4e;--okb:#dff1e7;--bad:#b0362b;--badb:#f8e1de;--wait:#8a5a00;--waitb:#fbefd6;--blk:#6b2d86;--blkb:#efe2f5;--unk:#5f6873;--unkb:#eceef1;color-scheme:light}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#111316;--panel:#191c21;--ink:#e8eaed;--muted:#9aa1ab;--line:#2c313a;--ok:#6cc79a;--okb:#14301f;--bad:#f08c80;--badb:#3a1c19;--wait:#e8b65a;--waitb:#362a10;--blk:#c9a0e0;--blkb:#2c1d36;--unk:#9aa1ab;--unkb:#22272e;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#111316;--panel:#191c21;--ink:#e8eaed;--muted:#9aa1ab;--line:#2c313a;--ok:#6cc79a;--okb:#14301f;--bad:#f08c80;--badb:#3a1c19;--wait:#e8b65a;--waitb:#362a10;--blk:#c9a0e0;--blkb:#2c1d36;--unk:#9aa1ab;--unkb:#22272e;color-scheme:dark}
*{box-sizing:border-box} body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 system-ui,"IBM Plex Sans","Noto Sans Arabic",sans-serif}
main{max-width:1060px;margin:0 auto;padding:24px 16px 80px} h1{font-size:1.6rem;margin:0 0 4px} h2{font-size:1.2rem;margin:34px 0 10px;padding-top:10px;border-top:1px solid var(--line)} h3{font-size:1rem;margin:16px 0 6px}
.muted{color:var(--muted)} table{width:100%;border-collapse:collapse;font-size:.88rem;margin:6px 0 12px;display:block;overflow-x:auto} th,td{text-align:start;padding:6px 8px;border-bottom:1px solid var(--line);vertical-align:top}
td.ok,span.ok{color:var(--ok);font-weight:700} td.bad,span.bad{color:var(--bad);font-weight:700} td.det{color:var(--muted);font-size:.8rem}
.v{display:inline-block;font-weight:700;font-size:.78rem;border-radius:99px;padding:1px 9px;white-space:nowrap} .v.ok{background:var(--okb);color:var(--ok)} .v.bad{background:var(--badb);color:var(--bad)} .v.wait{background:var(--waitb);color:var(--wait)} .v.blk{background:var(--blkb);color:var(--blk)} .v.unk{background:var(--unkb);color:var(--unk)}
.shots{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px} figure{margin:0;background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:6px} figure img{width:100%;display:block;border-radius:6px} figcaption{font-size:.78rem;color:var(--muted);padding:4px 2px 0}
.ar{direction:rtl;text-align:right;font-family:"Noto Sans Arabic","IBM Plex Sans Arabic",sans-serif} .card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:12px 14px;margin:8px 0}
pre{white-space:pre-wrap;background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px;font-size:.82rem;overflow-x:auto} .kpi{display:flex;gap:10px;flex-wrap:wrap} .kpi div{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:8px 12px} .kpi b{display:block;font-size:1.3rem}
.miss{color:var(--bad)}
"""
passed = sum(r['pass'] for r in R); NRUN = len(R)
counts = {}
for c in CLS['features']: counts[c['verdict']] = counts.get(c['verdict'], 0) + 1
H = [f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Rolex Oyster UAT</title><style>{CSS}</style></head><body><main>']
H.append(f'<h1>Rolex Oyster — user acceptance test of Video Director</h1><p class="muted">Development workspace only · free/local rendering · paid providers mocked or locked · {E(V["updated"])} · project <code>{E(PID)}</code></p>')
H.append('<div class="kpi">' + ''.join(f'<div><b>{n}</b><span class="v {VERDICT[k]}">{k}</span></div>' for k, n in sorted(counts.items())) +
         f'<div><b>{passed}/{NRUN}</b>UI checks passed in the final full run</div><div><b>{len(FIXED)}</b>defects found and fixed</div>' +
         (f'<div><b>{DEF["detected"]}/{DEF["planted"]}</b>planted defects found by the reviewer</div>' if DEF else '') + '</div>')
H.append(f'<div class="card"><b>Verdict.</b> {E(CLS["verdict"])}</div>')
fails = [r for r in R if not r['pass']]
H.append('<h3>Every run of the full UI journey</h3><table><tr><th>Run</th><th>Checks passed</th><th>Failures</th></tr>' + ''.join(
    f'<tr><td>{n}</td><td>{sum(x["pass"] for x in rs)}/{len(rs)}</td><td class="det">{E(" · ".join(x["stage"] + ": " + x["name"] for x in rs if not x["pass"])[:700])}</td></tr>' for n, rs in PRIOR.items()) +
    f'<tr><td><b>final (fresh copy)</b></td><td><b>{sum(x["pass"] for x in R)}/{len(R)}</b></td><td class="det">{E(" · ".join(x["stage"] + ": " + x["name"] + " — " + x["detail"][:160] + (" [" + x["note"] + "]" if x.get("note") else "") for x in fails)) or "none"}</td></tr></table>'
    '<p class="muted">Earlier runs found the defects listed in section 6; each was fixed and the whole journey was run again from an empty project.</p>')
H.append('<h2>1. Feature classification</h2><table><tr><th>Stage</th><th>Feature</th><th>Verdict</th><th>Evidence / why</th></tr>' +
         ''.join(f'<tr><td>{E(c["stage"])}</td><td>{E(c["feature"])}</td><td><span class="v {VERDICT[c["verdict"]]}">{c["verdict"]}</span></td><td class="det">{E(c["why"])}</td></tr>' for c in CLS['features']) + '</table>')
H.append('<h3>What is tested, what is mocked, what is missing</h3><ul>' + ''.join(f'<li>{E(x)}</li>' for x in CLS['separation']) + '</ul>')
# walkthrough
W = [('A', 'Create the project', [('A1-studio-home', 'Studio home'), ('A2-new-project-form', 'New video: idea, title, brand'), ('A3-project-overview-identity', 'Overview: steps, identity, final voice needs authorization'), ('A4-history-desktop', 'Version history (desktop)')]),
     ('B', 'Research and script', [('B1-research', 'Sourced claims; "first waterproof watch" marked avoid'), ('B2-script-v1-checks', 'v1: the unsupported claim is caught; approval refused'), ('B3-script-v3-typo-detected', 'v3: the planted typo is highlighted'), ('B4-flag-sheet', 'Highlight the word, say why, request the correction'), ('B5-correction-request', 'Correction request recorded'), ('B6-script-v4-diff', 'v4: exactly one word changed')]),
     ('C', 'Hooks', [('C1-hooks', 'Four hooks with spoken line, on-screen text and the rendered opening frames'), ('C2-hook-selected', 'H1 chosen → new script version to approve; payoff found in l13')]),
     ('D', 'Draft voice and pronunciation', [('D2-progress-while-voicing', 'Measured progress while the free draft voice records'), ('D3-after-restart-interrupted', 'Server killed mid-task: shown as interrupted, Resume'), ('D4-voice-takes', 'Waveform + timed words per line'), ('D5-word-sheet', 'Tap a word: it plays; flag it with kind, note, reading'), ('D6-voice-flag-open', 'Open pronunciation flag with the suggested reading'), ('D7-compare-old-new', 'Before / after takes of l9 side by side'), ('D8-take-decided', 'Old take rejected, corrected take approved after listening'), ('D9-voice-desktop', 'Decisions after reopening (desktop)'), ('D10-stale-line', 'Hook changed after voicing: the old take is marked stale, only that line to re-record'), ('D11-seek-refused', 'Jumping to the end of the waveform is not listening: decision refused (disposable copy)')]),
     ('E/F', 'Art', [('E1-support-matrix', 'What the studio can draw: supported / needs real material / prototype / paid / to build'), ('E2-concepts', 'Rendered concepts per scene; photo concepts blocked, never invented'), ('F1-fullscreen', 'Full-screen viewer'), ('F2-modification-sheet', 'Request changes'), ('F3-revision', 'v1 and v2 side by side'), ('F4-art-approved', 'Approved versions'), ('F5-note-waiting-operator', 'A free-text note waits for the art operator; no fake version'), ('F6-approved-art-revision', 'Changes to approved art: the approved version stays until the new one is approved')]),
     ('G', 'Storyboard and draft film', [('G1-storyboard', 'Storyboard from the approved script; durations from the takes; estimated final length'), ('G2-render-failed-blocker', 'A failed render shown as a blocker'), ('G3-render-progress-eta', 'Render progress in frame steps with a measured ETA'), ('G4-draft-player', 'The draft plays in the page')]),
     ('H', 'Independent review', [('H1-review-findings', 'Findings with scene, time, evidence still, fix'), ('H3-findings-decided', 'Accepted → correction task; dismissed with reasons')]),
     ('I', 'Progress dashboard', [('I1-overview-phone', 'Overview on a phone: latest film, steps, inbox, scenes, timings'), ('I2-overview-desktop', 'Overview on desktop'), ('I3-inbox', 'One inbox, grouped')]),
     ('J', 'Final gate', [('J1-final-plan', 'Exact text, voice, model, characters, blockers, the draft to approve'), ('J1b-gate-after-owner-decisions', "After the owner's decisions only the workspace lock remains"), ('J2-gate-refused', 'Authorization and generation refused')]),
     ('K/L', 'Correction loop and final state', [('K1-correction-closed', 'Accepted finding fixed, re-rendered, re-reviewed, task closed'), ('K2-gate-after-correction', 'Gate after the correction'), ('L1-gate-final', 'Final gate on the clean draft'), ('L2-overview-final', 'Project home at the end')])]
H.append('<h2>2. Walkthrough (phone screenshots unless noted)</h2>')
for st, title, shots in W:
    H.append(f'<h3>{st}. {E(title)}</h3><div class="shots">' + ''.join(img(n, 260, c) for n, c in shots) + '</div>')
    keys = st.split('/') + (['R'] if st == 'D' else [])
    H.append('<table>' + ''.join(res_rows(k) for k in keys) + '</table>')
# script, hook, storyboard
H.append('<h2>3. Script, hook and storyboard</h2><div class="card ar">' + ''.join(f'<p><b>{E(l["id"])}</b> {E(l["text"])}</p>' for l in lines) + '</div>')
H.append(f'<p class="muted">Script versions: ' + ', '.join(f'v{s["v"]} {s["status"]}' for s in V['scripts']) + f'. Hook chosen: {E(str(V["hooks"]["selected"]))} ({E(V["hooks"]["reasons"][:220])}…)</p>')
if sb['scenes']:
    rec = V['storyboards'][-1]
    H.append(f'<p>Storyboard v{rec["v"]}: <b>{rec["seconds"]} s</b> with the draft voice; about <b>{rec.get("est_final_seconds")} s</b> with the final narrator ({rec["words"]} words at {rec["pace"]["words_per_s"]} words/s, {E(rec["pace"]["source"])}).</p>')
    H.append('<table><tr><th>Scene</th><th>Start</th><th>Length</th><th>Visual</th><th>Art</th><th>Voice</th><th>Banner</th></tr>' + ''.join(
        f'<tr><td>{E(s["id"])}</td><td>{s["start"]}</td><td>{s["dur"]}</td><td>{E(s["technique"])}</td><td>{E(s["status"]["art"])}</td><td>{E(s["status"]["voice"])}</td><td class="ar">{E(s["banner"] or "")}</td></tr>' for s in sb['scenes']) + '</table>')
# film
H.append('<h2>4. The draft film</h2>')
if latest:
    H.append(f'<p>{E(latest["id"])} · {latest["seconds"]} s · 1080×1920 · rendered locally in {latest["render_s"]} s · decision: {E(str(latest.get("decision")))}. File: <code>{E(deliver.get("film", ""))}</code> (720p copy for sharing; the 1080p master is in the project).</p>')
    H.append(fileimg(OUT / deliver['sheet'], 900, 'One frame every 4 s'))
# timing
H.append('<h2>5. Measured times</h2><table><tr><th>Task</th><th>Units</th><th>Time</th><th>State</th><th>ETA check</th></tr>' + ''.join(
    f'<tr><td>{E(r["task"])}</td><td>{r["units_done"]}/{r["units_total"]}</td><td>{r["elapsed_s"]} s</td><td>{E(r["state"])}</td><td class="det">{E(json.dumps(r.get("eta_check")) if r.get("eta_check") else "")}</td></tr>' for r in V['runs']) + '</table>')
# defects
H.append(f'<h2>6. Defects found during the test and fixed in the workspace ({len(FIXED)})</h2><ol>' + ''.join(f'<li>{E(x)}</li>' for x in FIXED) + '</ol>')
if DEF:
    H.append(f'<h3>Planted defects in a disposable copy: {DEF["detected"]}/{DEF["planted"]} found</h3><table><tr><th>Planted</th><th>Expected</th><th>Found</th><th>Finding (time, severity)</th></tr>' + ''.join(
        f'<tr><td>{E(x["planted"] or "")}</td><td>{E(x["expect"])}</td><td class="{"ok" if x["found"] else "bad"}">{"yes" if x["found"] else "MISSED"}</td><td class="det">{E((str(x["finding"]["t"]) + " s · " + x["finding"]["severity"] + " · " + x["finding"]["detail"][:150]) if x["finding"] else "")}</td></tr>' for x in DEF['rows']) + '</table>')
    H.append(f'<p>Other findings on the defect copy: {E(json.dumps(DEF["extra_findings"], ensure_ascii=False)[:600])}. Accepting created a correction task: {bool(DEF["accepted_task"])}. Dismissed finding kept with its reason: {E(DEF["dismissed_kept"])}. Approved art, takes, scripts and storyboards unchanged after the review and the decisions: <b>{DEF["approved_work_unchanged"]}</b>.</p>')
# automated tests
H.append('<h2>7. Automated tests</h2>' + ''.join(f'<p>{E(x)}</p>' for x in CLS['automated']))
# independent review
H.append('<h2>8. Independent review (second agent)</h2><pre>' + E(AUDIT) + '</pre>')
if CLS.get('disagreements'):
    H.append('<h3>Where the two testers disagree, and what was done</h3><ul>' + ''.join(f'<li>{E(x)}</li>' for x in CLS['disagreements']) + '</ul>')
H.append('<h2>9. Remaining limitations, blockers and integration risks</h2><ul>' + ''.join(f'<li>{E(x)}</li>' for x in CLS['limitations']) + '</ul>')
H.append('</main></body></html>')
(OUT / 'rolex-oyster-uat-report.html').write_text(''.join(H), encoding='utf-8')
print(json.dumps(deliver), (OUT / 'rolex-oyster-uat-report.html').stat().st_size)

# Implementation and acceptance evidence

## Browser edition — October 18, 2026: rotating-partners fairness

Measured the pairing over 66 configurations (4–16 players, 1 court and full
courts, 6 / n−1 / 10 rounds) against the theoretical minimum. Before: 131
avoidable repeat partnerships in total (worst 9 in one event), opponents repeated
beyond the even-spread ideal in 59 cases. After replacing the greedy pairing
with a per-round cost search (`rotatingPlan` in `competition.mjs`, cached because
it ignores scores): 6 avoidable repeats in total (worst 2), 32 cases above the
loose opponent ideal, games-played spread never above 1, slowest first plan 16 ms
(16 players, 4 courts, 30 rounds). Measured with a throwaway script; **the Node
suite was not run by the agent**. A new `formats.test.mjs` case encodes these
bounds and the eight-player seven-round all-partners-once result; its assertions
were checked with the same script. Late arrivals/departures behave as before in
the scenarios in `desk.test.mjs` (checked by script, not the suite).

## Browser edition — October 5, 2026

### Community poster theme (local)

The homepage and shared tournament UI now follow Ryan's attached sports-poster
reference: cream paper, forest green, vermilion/gold/blue accents, a bundled
Anton display font, a live HTML headline and example scorecard, and two
transparent illustrations. Both raster assets are WebP (353,366 bytes combined);
the logo remains SVG. No PNG/JPEG files are shipped by the browser site. Prompts
and asset provenance are recorded in `site/ART-DIRECTION.md`; the font license
is included in the static output. The seven-format behavior remains intact.

Evidence from the theme pass:

- Standard, portable and project-subpath Hugo builds passed. The portable
  stylesheet's font path and the HTML's image paths resolve inside the package.
  The refreshed local offline ZIP includes the artwork and font.
- All 13 checks in the existing organizer browser smoke script passed after
  the shared header/home changes. Header backup download produced a valid
  copy; restoring it through the file input/preview/confirmation saved it again.
- Desktop (1440/1660), tablet (900), and mobile (320/390) layouts were inspected
  in Chromium. The 320-pixel document remained 320 pixels wide. Setup and play
  screens, the saved-event banner and header controls were also inspected.
- A project-subpath build reopened while network emulation was offline. An
  uncached probe failed while both WebP images decoded and the bundled font
  loaded. The worker cache contained the matching HTML, CSS, JS, SVG, WebPs
  and font. This verifies that local Chromium cache, not future hosting.
- WebP format/alpha, JavaScript syntax and whitespace checks passed. No new
  rules test suite or Django suite was run for the visual changes.

No commit, deployment or publication. Real Safari/tablet, voice/screen-reader
use, physical printing and portable `file://` opening remain unverified.

### Seven-format expansion (local)

Ryan requested the competitive and social formats discussed in this session.
The browser edition now provides round robin, round robin into playoffs,
pool play into playoffs, single elimination, true double elimination with a
conditional reset final, rotating partners, and king/queen of the court.
See `site/README.md` for the exact house rules and size/rotation limits.

Setup includes format-specific controls and game-count previews; roster arrows
set seeds without dragging. Pool qualification requires explicit review and
tie ordering. Confirmed qualification freezes the preliminary withdrawal record
so later withdrawals follow the existing bracket. Score correction/clearing and
reinstatement preview dependent results before clearing them. New-format scores
bind to their ordered opponents; version 2 restoration rebuilds and checks the
draw. Existing version 1 round-robin records and the storage key are preserved.

Evidence from this pass:

- **22 focused Node checks passed**: the nine original browser rules/storage
  cases plus 13 format cases. Includes bracket sizes 2–16, byes, bronze games,
  two-loss counts and reset finals, varied winners, uneven pools, qualification
  ties, balanced mixer appearances, ladder movement, dependent corrections,
  withdrawals after qualification, legacy recovery and malformed/new backups.
- **Browser checks passed in isolated Chromium contexts**: the original 13
  checks and 140 assertions in `browser-formats-smoke.js`. The latter completes
  all seven practice formats using actual controls, inspects print markup and
  exercises normal setup, seed movement and cancel/confirm correction paths.
  One rerun initially failed because the script advanced before an asynchronous
  score save; explicit waits for dialog/save completion fixed the harness, and
  the updated script passed. This is not physical printing evidence.
- **Backup UI checked separately**: a version 2 double-elimination copy restored
  its format and saved score; a copy with a changed opponent binding was rejected
  without replacing the current event.
- **320-pixel viewport check**: setup, roster, play and results stayed within
  the viewport; the expanded setup was inspected visually. No real-device or
  assistive-technology acceptance is implied.
- Standard and portable Hugo builds passed; JavaScript syntax and diff checks
  passed. The site/Pages check commands now include the new format tests.

GitNexus impact was run before edits. Resolved original functions reported LOW
risk; callback/file UNKNOWN results were checked in current source. The CLI
continued to report the older index (six commits behind); newly introduced
functions were not found in that graph. Ryan reported running analyze, but the
local metadata visible during this pass did not yet reflect a refresh. No
agent-run reindex or Django suite was performed.

All changes remain local and uncommitted. No publication or deployment occurred.
Still unverified: an attended event, real Safari/tablet use, screen reader/voice
operation, physical printouts, and opening the portable edition via `file://`.

### Earlier browser-edition evidence

The active single-organizer direction is implemented separately in `site/`.
The local Hugo build and targeted Node checks pass. Browser checks exercised
creation, a five-team/ten-match event, score validation/review/correction,
standings, backup download and restoration, malformed backup rejection,
second-tab overwrite rejection, and storage-full recovery. All four organizer
screens measured 320 CSS pixels wide at a 320-pixel viewport. A static build
reopened its saved event with a controlled offline network (an uncached probe
failed). These are synthetic local checks in one Chromium browser, not an
attended event, assistive-technology certification or cross-browser acceptance.

The nine targeted rules/storage cases cover pair uniqueness, no double
booking and minimum group counts for 2–16 entries on 1–8 courts; match IDs
stable across court counts; marked-walkover withdrawals and their validation; completed/deuce scores; tied standings
and corrections; malformed/foreign/oversized backups; failed persistence and
stale writers; and two simulated simultaneous writers through a lock. The
browser separately demonstrated actual stale-tab rejection with two open tabs.
No Django suite was run for this separate static implementation.

Later October 5 changes (court packing across rounds, mid-event court changes,
marked-walkover withdrawal/reinstatement, score-correction scroll/focus) have
the new rules cases above. The owner ran `node --test site/tests/browser-rules.test.mjs`
after the readability pass below: 9 of 9 passed (October 5, 2026, Node 22). A single manual pass in the in-app browser on a scratch build
exercised practice event, one score, withdrawal, unranked listing, reinstatement,
backup storage of the withdrawal, and a 2→1 court change with the score kept.
A later readability pass (larger small-print, "round" instead of "group", "copy" instead of "backup", plainer walkover and standings wording, "and"/"&"/"/" roster paste, aligned footer/step bar at 900–1194 px, save-status colour) was checked by measurement and screenshots in the in-app browser; the Node tests were run afterwards by the owner (9 of 9 passed), but the browser smoke script was **not** re-run after the wording changes.

An offline copy build (`--environment=portable`) was loaded over `http://localhost` from a
scratch folder and saved a practice event; opening it by double-click (`file://`) is
**unverified** and the Pages/zip workflow has never run.

That pass is now preserved as `site/tests/browser-smoke.js` (13 checks, all passing
when last pasted into the in-app browser on a scratch build). The earlier browser
evidence above predates these changes. `.github/workflows/site.yml` runs the Node
tests and a Hugo build in CI; it has not yet run on GitHub.

No publication, hosting change, external provider call, account system, shared
score editing or Django-data migration was performed. The archived Django edition
(`django-edition/`) is separate. See `site/README.md` for current
operating boundaries and recovery behavior.

# Browser tournament desk

Hugo builds this static site. The organizer uses a browser on one device.
No accounts, npm dependencies, external fonts, analytics, API, or cloud database.
The site is not published yet; it is prepared to publish as a GitHub Pages micro
site (see "Publishing and updating"). The earlier Django edition is intact.

## Organizer workflow

1. Start a tournament; name it, set the date and courts, choose singles/doubles.
2. Add 2–16 entries (up to 32 people in fixed doubles pairs). A pasted doubles
   list uses one pair per line: `Pat and Lee` (`&` and `/` also work). Identical names must be distinguished
   with initials or another recognizable display name.
3. Make the schedule. Every entry plays every other once. Groups use available
   courts without putting anyone on two courts at once, filling idle courts from
   later rounds when no one would play twice. An odd roster has byes.
4. Start a round (the screen's word for a group of games on the courts) when
   everyone is ready; finish it before starting the
   next. The tool does not measure minimum rest or predict finish times.
5. Enter scores, review the named winner, then confirm. Each match is one game
   to 11, 15 or 21, win by two. Correct or clear a saved score in the full schedule.
   The court count can be changed mid-event on the setup step; saved scores stay
   attached to their games and unplayed games are regrouped.
   **Withdraw** an entry on the teams step if it must leave: its played games
   stay, each remaining game becomes a marked walkover (the opponent gets the
   win, no points are recorded for either side), and the entry is listed last
   and unranked. **Reinstate** reverses it. Changing the roster still clears
   the schedule, scores and withdrawals.
6. See standings ranked by wins, point difference, then points scored. Remaining
   ties share a place. Print results or the schedule with blank score spaces.
7. Print the results, download a copy; reuse the settings and roster for another day if desired.

These are casual adult community events. There are no online registrations,
multiple divisions, live multi-device editing, elimination brackets, payment,
email, ratings, consent records, or sanctioned-event eligibility checks here.

## Saving and recovery

- One active tournament is stored per browser/origin/path. `localhost`,
  `127.0.0.1`, different ports and different paths are separate storage locations.
- State saves after submitting a setup/roster step and confirming a score.
  Unsubmitted text is not autosaved; navigation warns before discarding it.
- The saved badge appears only after the browser accepted the write. Storage
  failures keep the new record in the current tab, keep the old saved copy,
  display a warning and allow download of the current in-memory tournament.
- Browser locks serialize writes across tabs. A stale tab must explicitly load
  the current record before editing. A browser without Web Locks can still
  work in memory and export a backup, but cannot claim automatic saving.
- Keep using the same browser and address. Private browsing, clearing data,
  storage eviction, or device loss can remove the only local copy.
- **Download a copy** saves a versioned JSON file containing settings, names
  and scores. Save it somewhere retrievable. **Open a saved copy** validates and
  previews the event before replacing the current one. Backups contain player
  names; share them deliberately. Unknown fields are discarded. Matches and
  standings are recalculated. A backup is not authenticated proof of results.
- A corrupt saved record is not overwritten on opening the site. Download its
  original data from the recovery notice, or restore a known good backup.
- Starting a new/practice/reused event requires confirmation if an event exists.
  Only the latest event remains locally; export earlier events before replacing.
- Browser backups and Django archives are separate formats. No migration between
  them is implemented.

## Maintainer preview and build

Verified locally with Hugo **0.166.0** and Node **22.22.3**. Standard Hugo is
sufficient (the locally installed binary happens to be Extended). No Node is
required to build or use the site; it is used for the targeted checks.

From the repository root:

```sh
./play
```

Open http://localhost:1313/. This is a development preview; the offline worker
is intentionally omitted. The organizer of a future hosted site will simply
open its address, without running this command or installing Hugo.

```sh
hugo --source site --cacheDir "$PWD/site/.cache" --cleanDestinationDir --panicOnWarning
```

Output is the ignored `site/public/` directory.

### Publishing and updating (GitHub Pages)

`.github/workflows/pages.yml` runs the Node tests, builds with the real address
(`--baseURL` from `actions/configure-pages`) and deploys `site/public`. It has
never run. To go live, Ryan enables Pages once (repository Settings → Pages →
Source: GitHub Actions); after that, a change under `site/` reaching `main`
publishes automatically, and Actions → Run workflow republishes by hand. The
address will be `https://ryan258.github.io/open-pickleball-tourney/`. The
workflow replaces the old `docs/` deployment (one Pages site per repository).
Rehearsed locally: a build for that subpath loads, runs and saves under the
key `open-pickleball-browser:v1:/open-pickleball-tourney`. The offline worker
could not be exercised in the in-app browser (it cannot register any worker),
so check "Ready to reopen offline" in a real browser after the first deploy.

Rules for updating a live site:
- Saved events and backup files outlive any update. Never change the backup
  `version` or storage key without a migration that reads the old format; the
  tests include a backup without newer fields on purpose.
- An update never interrupts an open tab: the new worker waits until every tab
  is closed, and the footer says when an update is ready.
- GitHub serves a project site on the shared `ryan258.github.io` origin, so
  other pages under it share the browser's storage for that origin. Use a
  custom domain if that matters.
- The offline copy (below) is rebuilt from the same source on every publish, so
  it is always the same version as the site.
- The preview-only `noindex` meta tag and `robots.txt` (`Disallow: /`) are still
  in place: organizers need the link, search engines do not. Remove both
  (`site/layouts/home.html`, `site/layouts/robots.txt`) only on purpose.

### Offline copy (for organizers without a connection, or a screen/board computer)

The published site links "Download an offline copy" (a zip made by the same
workflow). Unzip it and double-click `index.html`; no server, install or internet
is needed. Maintainer build, which is also what CI builds and checks:

```sh
hugo --source site --destination /tmp/offline/open-pickleball-tourney --baseURL=/ --environment=portable
cp site/portable/README-FIRST.txt /tmp/offline/open-pickleball-tourney/
```

How it differs: links are relative to each page (`site/config/portable/hugo.toml`),
there is no service worker and no download link, and the footer says it is an
offline copy. Opened from a file, the page uses a simple save step instead of
browser locks (stale-tab detection stays; two tabs saving in the same instant are
not coordinated, so use one window). Browser storage is tied to the folder's
location: moving or renaming the folder, or switching browsers, shows an empty
tournament until a downloaded copy is opened. Served over plain `http://` on a
network address the browser offers no secure features, so automatic saving is
unavailable there (use https, `http://localhost`, or a double-click). CI fails the
build if the offline copy ever contains a root-relative link or a worker.
Verified: built and loaded from a folder over `http://localhost` (styles, practice
event, saving, ID fallback). **Not verified:** opening from a `file://` double-click
(the in-app browser cannot open file pages); check it in Chrome, Safari and
Firefox before telling organizers it works everywhere.

For a local static-build/offline preview (the existing Python environment is a
maintainer convenience, not part of the delivered static site):

```sh
.venv/bin/python -m http.server 8765 --bind 127.0.0.1 --directory site/public
```

Open http://127.0.0.1:8765/. Wait for **Ready to reopen offline in this browser**.
The worker caches only this site's shell, not participant records. Offline
reopening depends on that cache remaining present. Updates wait until all old
site tabs close; the HTML and hashed assets stay at one version while in use.
Keep a printed schedule and a downloaded backup for recovery. No cross-device
sync or network connection is needed for calculations and local saving.

## Focused checks and limits

```sh
node --test site/tests/browser-rules.test.mjs
```

Nine targeted checks cover pairing, minimum-group court packing and stable match
IDs for every supported entry count and court count, score boundaries,
ranking/correction, walkover/withdrawal rules and validation, backup validation,
failed storage, and stale/concurrent writers through a simulated browser lock.
They do not run the earlier Django suite, and the UI handlers in `app.js` have no
Node tests; the browser smoke script below covers them. Browser evidence is
recorded in `IMPLEMENTATION.md`.

**Browser smoke script.** Serve the site (`./play` or a static build), open it in a
window with no saved tournament (a private window is easiest), and paste
`site/tests/browser-smoke.js` into the DevTools console. It drives the real UI
through a practice event: score validation and review, correction from the full
schedule, withdrawal and reinstatement, the saved record, and a mid-event court
change. It prints a PASS/FAIL table, refuses to run over a saved tournament and
removes its own record. It is a Chromium-console check, not cross-browser or
accessibility evidence.

**CI.** `.github/workflows/site.yml` runs the Node tests and a standard-Hugo
`--panicOnWarning` build for changes under `site/`. It checks only; it never
deploys. Its first run is the first proof that standard Hugo is enough.

Still needed: a human-operated event rehearsal, real Safari/tablet coverage,
voice/screen-reader checks and physical printing. Automated/browser evidence
does not establish accessibility conformance or sanctioned-event readiness.

# Browser tournament desk

Hugo builds this static site. The organizer uses a browser on one device.
No accounts, npm dependencies, external fonts, analytics, API, or cloud database.
The site is not published yet; it is prepared to publish as a GitHub Pages micro
site (see "Publishing and updating"). The earlier Django edition is intact.

## Visual theme and assets

The community-poster theme uses warm cream, forest green, vermilion, gold and
dusty blue. The homepage pairs live HTML headlines and an example scorecard
with two transparent WebP illustrations. Setup, roster, scoring and results
share the palette and locally bundled Anton display font; form labels and body
copy retain a plain sans serif. No font or image needs a third-party request.

All raster artwork in the browser site is WebP: `pickleball-poster.webp`
(1448 × 1086, 293,402 bytes) and `pickleball-community.webp`
(800 × 400, 59,964 bytes). The court logo stays SVG. The original generated
PNGs are not shipped. Hugo fingerprints both illustrations and the font; the
service worker caches them with the HTML, CSS and JavaScript. Portable builds
use relative asset paths, including the font URL inside the stylesheet.

See [ART-DIRECTION.md](ART-DIRECTION.md) for the generation prompts and asset
provenance. The bundled font's license is in `static/licenses/Anton-OFL.txt`.

## Organizer workflow

1. Name the event and choose a format, court count and game target. Every match
   is one game to 11, 15 or 21, win by two. These are casual house rules.
2. Add names individually or paste one entry per line. Fixed doubles use
   `Pat and Lee` (`&` and `/` also work). Social formats take individual names
   and make doubles pairings. Distinguish identical names with initials.
3. Review the roster, game count, seeds and any pool assignments before making
   the schedule. Up/down buttons set seed order without dragging. High seeds
   get first-round byes; pools use snake seeding from this order. No skill
   rating is inferred. See the format table below for size limits.
4. Start the displayed court group together. Finish it before the next group.
   There is no promised rest interval or predicted finish time. Future bracket
   opponents are named as winner/loser placeholders; ladder rounds appear
   after the preceding round finishes.
5. Enter scores, review the named winner and any consequences, then confirm.
   Correct or clear scores from the full schedule. A correction that changes
   later opponents clears affected later scores **only after review**. Changes
   to preliminary results reopen playoff qualification; ladder winner changes
   clear later rounds. Unaffected scores remain.
6. For playoff qualification, review the preliminary standings and explicitly
   order remaining ties with selectors. A lower-ranked entry cannot jump ahead.
   Confirming qualifiers locks the bracket and preliminary withdrawal record;
   later withdrawals follow that bracket without reseeding.
7. Print schedules/results or download a copy. Reuse keeps the format, settings
   and roster for another day, with scores and advancement cleared. The home
   screen offers a practice tournament for every format.

| Format | Entries and settings | Advancement and results |
| --- | --- | --- |
| Round robin | 2–16 singles players or fixed doubles teams; 1–8 courts | Every pair meets once. Wins, point margin, then points scored; remaining ties share a place. |
| Round robin → playoffs | Same, with at least 2/4/8 entries for the selected playoff | Top 2, 4 or 8 qualify after organizer review; single-elimination finish. |
| Pool play → playoffs | 2 or 4 pools; at least two entries per pool, up to 16 total | Snake-seeded round robins; top two active entries per pool. Cross-pool first-round opponents. Unequal pools keep separate standings. |
| Single elimination | 2–16 fixed entries; 1–8 courts | One loss ends championship contention. Optional bronze game for semifinal losers; no full consolation bracket. |
| Double elimination | 2–16 fixed entries; 1–8 courts | Upper and lower brackets. Two losses eliminate an entry; reset final if the lower finalist wins the first final. Withdrawals end participation without inventing a score. |
| Rotating partners | 4–16 individuals; 1–8 available courts; 1–30 rounds | Full doubles courts, balanced appearances, fewer repeat partners/opponents. Not a complete partnership round robin. Individual places use win percentage, average point margin, then average points scored. |
| King / queen of the court | 4, 8, 12 or 16 individuals; exactly four per selected court; 1–30 rounds | Court 1 is highest. Winners move up, losers down; top winners/bottom losers stay. Partners split. Last-round court and outcome determine shared finishing places. |

Single-elimination playoffs can include a bronze game; without it semifinal
losers share third. Byes add no played wins/losses. Bracket placements come from
bracket finishes, not total wins, and appear when the event is complete.

**Court changes.** Fixed-entry formats can change court count during an event
without losing scores. Social formats lock court count after scheduling because
it defines their rotations. Reset the schedule to change it.

**Withdrawals.** Played games stay. An unplayed matchup involving a withdrawn
entry becomes a walkover: the other side wins without points. In a mixer, an
absent player forfeits their assigned side for that game. If both sides contain
an absent entry, neither receives a win. Reinstating restores playable matchups
and previews affected scores before clearing them. Withdrawn entries are
unranked. The court ladder needs a full roster, so it does not offer withdrawal:
back up the event and reset with a complete roster instead. Changing the roster
or format after scheduling requires explicitly clearing scores and advancement.

These are casual adult community events. There are no online registrations,
multiple divisions, live multi-device editing, payment, email, ratings, consent
records or sanctioned-event eligibility checks here. Team leagues, Swiss rounds,
full consolation brackets, timed games and multi-game matches are not included.

## Running a real day

- **Plan by time.** On the setup step, enter how many people or teams, the
  minutes you have and minutes per game (defaults 15/20/30 for games to
  11/15/21). The tool lists each format with a rough duration and marks the first
  that fits; **Use this** fills the form. These are estimates for planning only.
  The app still promises no finish time during play.
- **Late arrivals (rotating partners only).** On the roster step, add someone
  with the round they join. **Done for the day** removes someone from rounds
  not yet scored. Scored rounds never change; later pairings are re-made.
  Every round needs at least four people. Fixed formats cannot take late
  entries: their schedules are a promise to registered players (use rotating
  partners for drop-in play, or reset and restart).
- **Display board.** *Display board* on the Play step opens a second window
  (`#board`) with large type: games on court now, then the next group. Move it
  to a TV or second screen. It reads the same browser's saved record and updates
  by itself, so it works on this device only. It is not a link for players'
  phones.
- **Share results.** Results step: opens the phone's share sheet, or copies plain
  text for a group chat. Names are included on purpose; the organizer chooses to
  share.
- **Delete a tournament.** Home screen or setup step, after a confirmation that
  offers a backup download first. Deleting uses the same lock and stale-tab check
  as saving, so another tab's newer work is never discarded.
- **Undo last score** (this tab only, until the next score or reload), **screen
  stays awake** on the Play step and the board where the browser supports it,
  and a **High contrast** toggle for outdoor glare (remembered per browser).
- Backups with late arrivals use version 2 with a `windows` field. Older apps
  reject them rather than misreading.

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
  standings are recalculated; new-format scores must match their saved opponents. A backup is not authenticated proof of results.
- A corrupt saved record is not overwritten on opening the site. Download its
  original data from the recovery notice, or restore a known good backup.
- Starting a new/practice/reused event requires confirmation if an event exists.
  Only the latest event remains locally; export earlier events before replacing.
- Round-robin copies use version 1. Other formats use version 2 so older apps
  reject them instead of misreading them. This app reads both; existing version 1
  records need no manual migration. The browser storage key stays unchanged.
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
node --test site/tests/browser-rules.test.mjs site/tests/formats.test.mjs site/tests/desk.test.mjs
```

The original nine checks cover round-robin pairing/court packing, stable match
IDs, score boundaries, standings, withdrawal rules, backup validation, failed
saving and stale/concurrent writers. Five `desk.test.mjs` checks (late arrivals and departures, the time planner, shareable
results text and the board model) were added October 6; all 28 checks across the three files passed in Ryan's run (including a delete-vs-stale-tab storage check). Thirteen additional format checks cover
2–16-entry brackets, double-final resets and two-loss invariants, bronze games,
pools and qualification ties, balanced mixer rests, ladder movement, dependent
score corrections, frozen playoff seeding, withdrawals and versioned restoration.

**Browser smoke scripts.** Serve the site, use a fresh/private browser window
with no saved event, and paste `site/tests/browser-smoke.js` or
`site/tests/browser-formats-smoke.js` into DevTools. Each refuses to overwrite an
existing saved event and removes its own record. Reload afterwards to clear the
in-memory test state. The first checks the original round-robin workflow; the
second completes all seven formats through the real controls, checks print
markup, and exercises new setup, seeding and correction confirmation. These
are Chromium checks, not cross-browser or accessibility certification.

**CI.** `.github/workflows/site.yml` runs the Node tests and a standard-Hugo
`--panicOnWarning` build for changes under `site/`. It checks only; it never
deploys. Its first run is the first proof that standard Hugo is enough.

Still needed: a human-operated event rehearsal, real Safari/tablet coverage,
voice/screen-reader checks and physical printing. Automated/browser evidence
does not establish accessibility conformance or sanctioned-event readiness.

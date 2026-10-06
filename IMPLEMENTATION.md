# Implementation and acceptance evidence

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
score editing or Django-data migration was performed. The original application
and its limitations below remain distinct. See `site/README.md` for current
operating boundaries and recovery behavior.

---

**October 4, 2026 · America/Chicago.** The local application is runnable. The entire target specification and its R1/R2/R3 release gates are **not complete**. This file separates code from the evidence actually obtained.

## Delivered local workflow

Django 5.2 LTS / Python 3.13 modular monolith, server-rendered templates, vanilla JavaScript, transactional SQLite and a durable database mail outbox. Dependencies are pinned; PostgreSQL is configurable but untested. The initial migration, isolated demo seed, `./tour` launcher, local operator link and SQLite recovery commands exist.

Public discovery, event pages, directory privacy, email-link login/registration, separate doubles acceptance, assisted registration, CSV preview/import, waitlist offers/expiry, private accommodations, per-person check-in, draw publication, schedule proposals/manual pins, court dispatch, staff scores, review/confirmation, corrections, standings, partial/final results, role scoping, promotion assets, manual financial records, approval notes, private archives and generic result packages are implemented to the limits below.

The UI uses labeled native controls and list/table representations. It has no drag-only requirement, CDN, external fonts, frontend build or AI service dependency. This is an implementation property, not accessibility conformance evidence.

## Verification record

| Evidence | Observed result | Limit |
| --- | --- | --- |
| `manage.py check` | Passed | Django configuration/model checks only |
| Initial migration + `makemigrations --check --dry-run` | Local SQLite migration passed; no drift | PostgreSQL migrations not exercised |
| `tourney.tests.test_engine` | 4 tests passed; 2–16 entrant fixtures, elimination/reset loss counts, score validation and three-way tie | Bounded deterministic branch patterns; not every possible tournament history |
| `tourney.tests.test_runtime` | 29-test runtime pass, followed by five focused checks after final hardening (two new): 31 distinct runtime cases exercised | Disposable SQLite tests, primarily sequential requests/transactions |
| Synthetic service pilot in runtime tests | 32 adults / 16 teams / four divisions / four courts / 24 matches; check-in, schedule, scores and final results complete | Controlled test time; not an attended event, load measurement or full exception/disruption rehearsal |
| Browser scoring path | Demo login, four check-ins, start, 11–7 review and confirmation succeeded | One browser engine; synthetic data; broader creation/registration/correction journeys remain to inspect |
| Responsive measurements | Match page at 320 and 1,280 CSS pixels: document width matched viewport | Larger native IAB captures were clipped; not complete visual/assistive-technology coverage |
| Backup and isolated restore | Synthetic SQLite snapshot/hash/integrity and restore suppression succeeded | No measured RPO/RTO, off-machine recovery, or PostgreSQL recovery |
| Shell/Python syntax and static collection | Passed | Not a deployment/security certification |

The latest verification evidence is summarized in roadmap.md. The 35-test suite passed on October 5 before that day's review fixes; the regression tests added with those fixes are unrun until the owner runs `manage.py test`. No provider call, production deployment or external message was performed by the agent.

## Acceptance coverage

“Implemented / focused” means some relevant code and targeted evidence exist. It does **not** mean the entire acceptance obligation or release gate has been proven. “Partial” names a remaining contract or evidence gap. IDs below account for all 64 criteria.

| Criteria | State | Evidence and remaining work |
| --- | --- | --- |
| AC-001 | Partial | Event-scoped permissions, scoped foreign-key lookups, export permissions and private responses. Complete cross-tenant object-existence and role matrix still needs coverage. |
| AC-002 | Implemented / focused | Assigned-match scorer read/write guards and immediate grant revocation tested. No protected streaming subscriptions exist. |
| AC-003 | Implemented / partial evidence | Required event fields and ranges gate publication; draft forms/routes render. Browser creation/publication journey remains open. |
| AC-004 | Implemented / focused | Public-only directory, noindex on private/unlisted pages, private HTML/JSON/CSV/flyer/QR access tested. |
| AC-005 | Implemented / focused | Clone copies reusable settings/courts/divisions into a fresh private draft; private records and approval excluded. |
| AC-006 | Partial | Event serialization and capacity logic implemented; real simultaneous independent clients have not been tested. |
| AC-007–AC-008 | Implemented / partial evidence | Individual token acceptance, incomplete teams, active-division membership uniqueness, identity reuse and replacement guards. Complete doubles concurrency/expired-invitation fixture matrix remains. |
| AC-009 | Implemented / focused | Waitlist release and timed expiry tested; paused expired entries and closed-registration admission gates implemented. |
| AC-010 | Implemented / focused | Event-local age date, adult gate, maximum partner skill, inclusive minimum/exclusive maximum, self-reported provenance; numeric skill regression passed. |
| AC-011 | Implemented / focused | Bounded CSV, row errors/duplicate preview, selection, revision-bound atomic import, explicit notice opt-in. Lost-response replay after preview removal needs refinement. |
| AC-012 | Implemented / partial evidence | Forms and server admission enforce adults 18+; no junior bypass enabled. Broader import/assistance boundary fixtures remain. |
| AC-013 | Implemented / focused | Active-member acceptance/check-in gate; browser checked four individual players before starting their doubles match. Missing-partner UI uses a generic readiness error. |
| AC-014 | Partial | Match page flags calls older than ten minutes without automatic forfeits. Full configurable grace/escalation workflow absent. |
| AC-015–AC-016 | Implemented / focused | Pair uniqueness/count/rest-round and seeded single-elimination/bye fixtures for 2–16 entrants pass. |
| AC-017 | Implemented / partial evidence | Frozen draw inputs/hash, deterministic generation and stale-preview checks. More concurrent edit fixtures needed. |
| AC-018–AC-020 | Implemented / focused | Completed/deuce/game-sequence validation, retained invalid form values, staff administrative outcomes and separate incomplete games; engine/runtime and browser score evidence. |
| AC-021 | Implemented / focused | Casual ranking: wins, complete normal head-to-head group, differential, points, seed; visible deciding criterion and three-way fixture. More mixed administrative tie fixtures needed. |
| AC-022 | Partial | Event lock, match revision and unique confirmed-result constraint; replay tested, actual simultaneous competing confirmations not tested. |
| AC-023 | Partial | Shared-person, interval/rest and private-accommodation checks implemented. More cross-division/manual pin conflicts and simultaneous-change fixtures needed. |
| AC-024 | Partial | Calls/starts serialize and reserve court/people; actual multiple-client race evidence remains. |
| AC-025 | Implemented / focused | Active occupancy blocks starts; scheduling now retains unscheduled active matches and actual completion/rest intervals. Focused regression passed. |
| AC-026 | Partial | Resolved ready matches receive assignments or blockers. Unresolved future bracket rounds/event finish forecasting not implemented. |
| AC-027 | Partial | Event holds prevent new starts; court holds suspend active play. Resume uses a separately requested preview; automatic reviewable resumption proposal absent. |
| AC-028–AC-029 | Implemented / focused | Pre-start elimination correction propagates; started descendants block ordinary correction and require explicit incident/void workflow. Pool qualification corrections are conservatively blocked pending requalification workflow. |
| AC-030 | Implemented / partial evidence | Corrected final divisions reopen, old final snapshot remains in audit, packages become correction-required. Full certification/correction history fixtures remain. |
| AC-031 | Implemented / focused | Incomplete or incident-bearing divisions cannot certify; explicit partial result snapshot/action added. Broader interrupted/archived lifecycle cases need review. |
| AC-032 | Implemented / partial evidence | Printable current-revision flyer, text URL, QR, copyable invitation. HTTP render checked; physical QR scan not tested. |
| AC-033 | Partial | Assets display revision and event settings update pages; registry/notification of previously downloaded obsolete assets absent. |
| AC-034–AC-035 | Implemented / focused | Stable delivery identity, durable claim, saved-local/accepted distinction, uncertain-send quarantine, reviewed bounded retries, and independent committed event state tested against local/mock transport. No real provider acceptance evidence. |
| AC-036 | Implemented / focused | Public allowlists, contact-free roster export and representative privacy checks. All role/route/history variants still need review. |
| AC-037 | Missing | Participant retention deadlines, holds, deidentification and derived-export invalidation not implemented. Expired-token cleanup is narrower. |
| AC-038–AC-039 | Missing / disabled | No promotional campaign sending or guardian/junior registration. Marketing outbox rows suppressed. |
| AC-040 | Implemented / partial evidence | Staff-recorded ledger, receipt reference/actor, capped refunds and preserved receipts through replacement. No payment processor verification implied. |
| AC-041–AC-043 | Missing / disabled | No online payment provider, webhooks, paid reservations or provider refund/reconciliation adapter. |
| AC-044 | Implemented boundary | Casual operations work without providers. Provider-specific actions are absent/disabled. |
| AC-045–AC-048 | Partial / external gate closed | Approval notes are organizer-recorded only. Software eligibility, rule profiles, approval verification, expiry and eligibility sources are not connected; sanctioned operation is explicitly unavailable. |
| AC-049–AC-050 | Partial | Hash/revision-bound generic packages and local correction-required state. No transmission, acknowledgment or provider correction adapter. |
| AC-051–AC-053 | Partial | Native labels, keyboard controls, touch targets, list/table brackets, reduced-motion CSS and narrow layout measurements. Complete keyboard, screen-reader, mobile and voice-control evidence remains open. |
| AC-054 | Partial | Offline/stale indicators, pauseable revision polling, explicit refresh, unsaved-form warning and printable pack. Server draft recovery, cached offline public views and full network-drop reconciliation rehearsal absent. |
| AC-055 | Implemented / focused | Same-key score replay returns the original outcome without duplicate result/audit; input/key conflicts rejected. Settings edits and removed-preview imports need fuller lost-response recovery. |
| AC-056 | Implemented / focused | Ambiguous/nonexistent local times rejected; explicit fold or offset accepted; DST edge tests passed. |
| AC-057 | Partial | Allowlisted/hash-checked atomic event round trip, ID remapping, ownership provenance, private draft and external suppression tested. Clean-install/cross-version/legacy attribution and full consent-history portability remain open. |
| AC-058 | Implemented / partial evidence | Escaped templates, formula-safe CSV, upload bounds, schema/hash/FK allowlists and malformed archive/ID checks. Nested JSON/domain validation needs broader adversarial fixtures. |
| AC-059 | Unverified | No workload latency/freshness envelope measured. Do not infer it from the fast synthetic tests. |
| AC-060 | Partial | Consistent SQLite backup/restore with integrity and suppression executed. Actual RPO/RTO, off-machine and production/PostgreSQL recovery not measured. |
| AC-061 | Partial | Place-then-pool-order qualification exists; unequal pool end-to-end and corrected qualification need fuller evidence. |
| AC-062 | Implemented / bounded evidence | Pure double-elimination graph/loss/reset fixtures cover sizes 2–16 with fixed outcome patterns. Database/UI reset scenarios still need verification. |
| AC-063 | Missing / disabled | Player-submitted score/dispute workflow absent; scores remain staff-entered. |
| AC-064 | Partial | Main 32-player service pilot completed. Waitlist/replacement are separate fixtures; combined exception/disruption/human-operated event evidence remains open. |

## Material gaps beyond individual criteria

Individual `EntryMember` acceptance version/time/method and the entry's quoted policy are retained, but an immutable copy of **every** version actually accepted by each person is not yet stored. Do not claim complete consent history after multiple policy changes. Prior replaced members remain in the database, excluded from current operational membership; their old participant grants cannot operate the entry.

Database constraints, transactions and idempotency are implementation safeguards. Independent-process concurrency, SQLite busy recovery and PostgreSQL-specific behavior require direct evidence. Serialized test calls cannot substitute for that.

The project has no selected license, no deployment, no provider enrollment, and no sanctions/software eligibility evidence. The local synthetic demo is the deliverable of this continuation, not a claim of a finished tournament platform.

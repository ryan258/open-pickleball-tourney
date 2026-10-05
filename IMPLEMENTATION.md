# Implementation and acceptance evidence

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

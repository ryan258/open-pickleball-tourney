# Open Pickleball Tourney — roadmap and restart handoff

**Status: Local application runnable; R1 implementation and release evidence incomplete**  
**Updated: October 4, 2026, America/Chicago**  
**Workspace: `/Users/ryanjohnson/Projects/open-pickleball-tourney`**

## Start here

Read [README.md](README.md) for the short launcher and [IMPLEMENTATION.md](IMPLEMENTATION.md) for delivered behavior, acceptance coverage and limits. [spec.md](spec.md) remains the target. The original paused scaffold handoff is retained in [docs/handoff-2026-10-03.md](docs/handoff-2026-10-03.md); its “not runnable” status is historical.

```sh
./tour
```

The app runs at `http://127.0.0.1:8000/`. Choose **Open organizer demo**. The launcher uses `.data/demo`, preserves existing demo work, forces file-based mail, and manages a worker. Normal local events use `./tour serve` and `.data` instead. See [OPERATIONS.md](OPERATIONS.md) for trusted local login, delivery reconciliation, backup and restore.

No Git repository exists in this workspace. No staging, commits, pushing, deployment, external publication, actual participant messages, provider enrollment or license selection occurred. The user’s local implementation authorization remains in force; external actions remain owner-controlled. Follow the supplied operator capsule and use targeted verification. Give Ryan long/full-suite commands rather than repeatedly running them. No subagents were used.

## Completed in the October 4 continuation

- [x] Added URL configuration and implemented every formerly missing template-linked handler: clone, roster import, participant accommodations, transfer/replacement, scorer assignment, CSVs, archive import/export, reporting packages.
- [x] Added responsive CSS and JavaScript for offline/stale indicators, pauseable polling, copy, print, confirmation and unsaved-form warnings. No external frontend assets or compilation required.
- [x] Added and reviewed the initial Django migration; migrated the isolated local demo database. Migration drift and Django checks pass.
- [x] Added the idempotent demo seed: 32 adults, 16 teams, four divisions/courts, 24 matches, plus an empty upcoming registration practice event.
- [x] Added a durable mail worker, waitlist maintenance, interrupted-send handling and explicit uncertain-delivery reconciliation.
- [x] Added `./tour`, trusted local operator-link creation, and consistent SQLite backup/isolated restore commands.
- [x] Enforced assigned-match scorer reads/mutations and current role revocation; staff/court operations now use revision/idempotency guards.
- [x] Bound link acceptance to the displayed policy version, corrected unique-person capacity counting, retained separate incomplete-game scores, blocked pool corrections after qualification, and made court holds suspend active play.
- [x] Added accessible manual court/time pinning and private availability editing; future plans affected by accommodation changes are cleared for re-proposal.
- [x] Added explicit partial results, correction-required package state, no-show decision notice after a ten-minute call, and private entry-recovery forms.
- [x] Added allowlisted, hashed archives with scoped relationship validation, atomic restore, ID remapping, private draft status and external-action suppression.
- [x] Added focused engine/runtime regression checks and honest setup/recovery/coverage documentation.

## Evidence actually obtained

- Engine module: **4 tests passed** including round-robin pair coverage and deterministic single/double-elimination loss counts for 2–16 entrants, completed/incomplete score boundaries, and a three-way tie.
- Runtime module: **31 distinct cases passed**: a 29-test runtime run, followed by five final targeted checks including two new cases. Route/template smoke, CSRF, private responses, assigned scorer/revocation, link preview/consumption/policy mismatch, capacity identity reuse, waitlist expiry, CSV preview/import/injection, score idempotency, replacement history, correction dependencies, actual rest/active reservations, staff replay, outbox failure/reconciliation, archive round trips and malformed archives are covered.
- A service-level synthetic pilot registered/checked in 32 adults, scheduled and completed 24 matches, finalized four divisions, and generated permitted results. Controlled test time was used; this is not an attended tournament or a load exercise.
- Browser: local demo sign-in → four individual check-ins → start → enter 11–7 → review → confirm succeeded. Those four check-ins and one completed match remain in `.data/demo` deliberately; the rest of the demo remains available.
- The match page measured at **320 and 1,280 CSS pixels without document-level horizontal overflow**. Native IAB screenshot capture was clipped at larger viewport overrides; full desktop visual inspection and the specified device/assistive-technology matrix are still open.
- SQLite backup and separate-directory restore succeeded with synthetic data. Restore invalidated old tokens/sessions and disabled event email. No measured disaster-recovery RPO/RTO claim.
- No full-suite command, GitNexus analysis, PostgreSQL test, live provider operation, production deployment or accessibility conformance evaluation was run.

## Next implementation work

Continue from the current source; do not recreate the project or restart specification drafting.

1. **Complete R1 consent/history and retention:** keep immutable policy text for every individual acceptance across policy changes, implement configured participant retention/holds/deidentification, derived-export invalidation, access/deletion requests, and organization ownership transfer.
2. **Finish admission/operator recovery:** richer duplicate-identity reconciliation, batch import retry recovery after lost responses, one-action incomplete-member acceptance/invitation recovery, and fuller no-show workflow evidence. Preserve explicit individual consent and waitlist fairness.
3. **Finish schedule/correction contracts:** forecast unresolved bracket rounds, reviewable resume proposals, pool qualification recomputation, and all suspended/void/partial/archive combinations. Keep actual occupancy and rest authoritative.
4. **Finish draft/recovery UX:** real server draft saving/recovery (current `data-draft` is only a warning hook), complete offline/reconnect paper reconciliation rehearsal, and clear stale-state feedback across tabs.
5. **Strengthen portability validation:** cover malformed nested JSON/domain states, legacy actor/consent provenance through repeated archive exports, and clean-install/cross-version restore drills. Current hashes establish integrity only, not provenance trust.
6. **Real database concurrency and deployment evidence:** competing last-spot admission, court calls/starts, and score confirmations using independent connections/processes on SQLite and PostgreSQL; add meaningful busy/conflict behavior as needed. Current sequential transactional tests are not this evidence.
7. **Remaining acceptance/release work:** complete the exception/disruption rehearsals, browser/device/screen-reader/voice matrix, and measured performance/recovery envelope. Follow the coverage table in IMPLEMENTATION.md; none of R1/R2/R3 is certified complete.

## R2/R3 and external gates

- Junior/guardian registration, player score submission/disputes, multiple venues and larger capacities remain disabled/missing.
- Pools and double-elimination source exists with bounded engine fixtures; end-to-end fixtures and pool correction/requalification still need work before expanded-format support claims.
- Campaigns, opt-in partner discovery, sponsors, attribution, SMS and online payments are not delivered.
- Ratings submission, payment webhooks/refunds, sanctioned profiles, eligibility checks, software approval and real receiving-body acceptance require actual providers/configuration/permission. Do not fake them or infer approval from notes.
- License selection remains Ryan's decision before any open-source distribution claim.

## Owner-run verification commands

```sh
# Focused current modules (fast locally)
.venv/bin/python manage.py test tourney.tests.test_engine tourney.tests.test_runtime

# Full discovery, when Ryan chooses to run it
.venv/bin/python manage.py test
```

A PostgreSQL concurrency/load command should be provided only after its actual harness and isolated test database are configured. Do not offer a placeholder command as evidence.

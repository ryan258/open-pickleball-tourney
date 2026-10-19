# Open Pickleball Tourney — roadmap and restart handoff

## Active direction — October 5: one organizer, one device

Ryan selected the static Hugo browser edition. The implementation is in `site/`;
`./play` starts its local development preview. Use `site/README.md` for its scope,
verification, recovery, and build commands. The October 5 section of `spec.md`
is its acceptance contract. The Django edition and its roadmap are archived in
`django-edition/`.

Implemented: guided setup and roster, bulk entry and seed-order buttons; seven
formats (round robin, round robin/playoffs, pools/playoffs, single elimination,
double elimination, rotating partners and king/queen); qualifier review,
conditional reset finals, correction previews and protected score bindings;
mid-event court changes for fixed entries, marked-walkover withdrawal,
score review/correction, derived standings, printable schedule/results,
browser-local storage, stale-tab rejection, versioned backup/restore (v1 and v2),
practice event and reuse, and static-build offline PWA caching.

Added October 6:
- Desk tools: time planner (`planFormats`), late arrivals and early departures for rotating partners (`windows`), TV/wall display board (`boardModel`), plain-text results sharing (`resultsText`), undo last score, screen wake lock, high contrast mode.
- Community poster aesthetic: vintage sports poster styling, local Anton typography, transparent WebP artwork assets, and local font license.
- Documentation & rules: comprehensive [101 Really Good Pickleball Rules Questions (with Answers)](docs/101-really-good-pickleball-rules-questions-w-answers.md) cross-referenced against the 2026 USA Pickleball Official Rulebook and explicitly detailing casual house rules differences.

Added October 18–19:
- Phone-first layout & quick start: quick-start home card with instant format suggestions (badges for suggested/fastest formats based on headcount, courts, and time), bottom-pinned thumb navigation for mobile viewports (<= 760px), bottom-sheet dialogs, touch-friendly point steppers (- / +) and one-tap "Game {target}" score fill buttons.
- Rotating partners fairness: cost-searched pairing schedule (`rotatingPlan`) balancing rest intervals across rounds (spread <= 1), minimizing repeat partnerships (benchmarked across 66 configurations), and preventing consecutive sit-outs when bench <= courts.
- Storage & lifecycle safeguards: verified storage removal rejecting silent browser failures, and clean state reset for social arrival/departure windows and score bindings on format change or event restart.
- Archival: full Django edition archived to `django-edition/` alongside its showcase, operational docs, and CI definitions; root repo dedicated purely to the browser edition.
- Verification: 32 focused Node tests passing across `browser-rules.test.mjs`, `formats.test.mjs`, and `desk.test.mjs`; standard and portable Hugo builds clean.

Next: Ryan's review of the local UI with a realistic event; real tablet,
keyboard/voice/screen-reader and physical print checks; choose a stable public
address (Pages is enabled and `pages.yml` has deployed successfully on Oct 6 and Oct 19; a project
site's address is `https://ryan258.github.io/open-pickleball-tourney/`). No hosting changes,
remote services, accounts, payments, or shared writers were added.

# Feature: Open Pickleball Tourney

## October 5 expansion: common tournament and social formats

Ryan requested all formats discussed for the browser edition. This extends the
original round-robin contract below; one organizer/device, fixed scoring, local
saving and the 16-entry ceiling remain. Implementation and verification evidence
belong in `IMPLEMENTATION.md`.

- Seven choices: round robin; round robin into a top-2/4/8 single-elimination
  playoff; 2 or 4 round-robin pools into a playoff (top two per pool); single
  elimination; true double elimination; rotating-partner doubles; king/queen
  of the court. Single-elimination playoffs offer an optional bronze game,
  not a full consolation bracket. These are explicit casual house rules.
- Fixed formats use singles or fixed doubles. Roster order is seeding order,
  editable with buttons before scheduling. Byes go to high seeds. Pools use
  snake seeding; playoff openings pair winners against runners-up from other
  pools. No ratings service or inferred skill level.
- Pool and round-robin playoff standings use wins, point difference, then
  points scored. The organizer reviews advancement and explicitly orders any
  remaining ties using selectors. A lower-ranked entry cannot replace a
  higher-ranked entry. Withdrawn entries cannot qualify. Pool ranks are kept
  separate; unequal pools are not compared by raw totals.
- Double elimination has upper/lower brackets and a reset final if the upper
  winner loses the first final. A bye is not a win or a loss. Withdrawals can
  end participation without two played losses. Bracket places follow bracket
  finishes rather than total wins; unfinished brackets do not claim final places.
- Rotating partners accepts 4–16 individuals, 1–8 available courts and 1–30
  rounds. Use as many full courts as possible, balance appearances, and prefer
  less-repeated partners/opponents. This is a mixer, not a guarantee that all
  possible partnerships occur. Court count stays fixed once started. Individual
  ranks use win percentage, average
  point difference, then average points scored; real ties remain ties.
- King/queen accepts 4, 8, 12 or 16 individuals, exactly four per selected
  court, and 1–30 rounds. Court 1 is highest. Winners move up one court, losers
  down one; the top winners and bottom losers stay. Incoming pairs split into
  new partnerships. Next-round pairings wait for all current-round scores.
  Final court and last-round outcome determine shared finishing places.
  Roster/courts remain fixed once started; an absence requires a backed-up
  restart with a complete roster. No silently invented substitute or result.
- Show format rules, game counts/ranges, seeding/pool assignments and limits
  before scheduling. Keep every named court, score, advancement and print view
  usable without drag interactions. Future opponents display as placeholders.
- Preview destructive consequences of corrections, clearing scores and
  withdrawal/reinstatement. Preserve scores whose participants still match;
  clear results dependent on changed advancement. Any preliminary result
  change reopens playoff review. Ladder winner changes clear later rounds.
  Confirming qualifiers freezes preliminary withdrawal status; a withdrawal
  during playoffs follows the locked bracket without reseeding the event.
- New-format scores bind to their ordered participants. Restore rebuilds
  schedules and rejects unreachable scores, wrong pairings, invalid seeds,
  unsupported formats and malformed settings. New formats use backup version 2;
  version 1 remains readable as round robin. Keep the existing storage key.
- Focused checks cover all seven formats, odd/uneven sizes, byes, court bounds,
  double-final reset, ties, corrections, withdrawals, social partner/ladder
  movement, restore boundaries, legacy recovery and real browser controls.

References for terminology (not claims of sanctioned support):
[USA Pickleball formats](https://usapickleball.org/sanctioning/formats/) and
[Dogwood Pickleball ladder rules](https://www.dogwoodpickleball.ca/kings-queens-rules.html).

## October 5 direction: one organizer, one device

Ryan selected a Hugo static site for an organizer using one computer or tablet.
This is the active implementation direction. The earlier Django specification
(archived in `django-edition/spec.md`) is historical, not the acceptance contract
for this smaller browser edition.

The browser edition lives in `site/`. Its bounded first workflow is one casual
adult event, 2–16 fixed singles players or doubles teams, 1–8 courts, and one
round robin. Setup → teams → play → results must work without accounts, a
database server, email, or a command line for the eventual hosted-site user.
Hugo is a maintainer build tool. The intended host is a GitHub Pages micro site
updated from `main`; publishing remains Ryan's action.

- Large labeled controls, visible focus, touch/keyboard operation, minimal
  typing, bulk roster entry, practice data, and printable schedules/results.
- One game per match, target 11/15/21 and win by two. Courts are assigned in
  successive groups; the next group waits for the current group to finish.
  These are organizer-selected casual rules, not sanctioned-event claims.
- Every pair meets once; nobody plays twice in a group; an odd roster gets
  byes. Idle courts are filled from later rounds. No estimated times or promise
  of a minimum rest interval. Court count may change mid-event without losing
  saved scores.
- Withdrawal keeps played games; each remaining game is a marked walkover
  (opponent wins, no points recorded). Withdrawn entries are listed last and
  unranked, and can be reinstated.
- Review named sides and winner before saving a valid score. Corrections and
  clearing a score update derived standings. Ties use wins then differential
  then points scored, with genuine remaining ties sharing a place.
- Browser-local saving with honest failure feedback, stale-tab protection,
  versioned downloadable backups, validated restoration, and explicit review
  before replacing the active event. Imported schedules/standings are rebuilt
  from validated inputs; imported HTML is never executed.
- Printable blank score sheets and results; reusable event settings/roster.
  Starting again never silently deletes the current tournament.
- Offline reopening requires a successfully cached static build at the same
  address. Local data belongs to that browser/address; backup files are the
  portable recovery path, not automatic cross-device synchronization.
- Online registration, multiple writers, payments, email, ratings, sanctioned
  formats and importing Django archives are outside this edition.

Verification is targeted to scheduling, scoring/ranking, backup boundaries,
storage recovery and the browser workflow. Human event-day and assistive-tech
acceptance remain separate from automated checks.


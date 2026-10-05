# Feature: Open Pickleball Tourney

**Status:** Target product specification, draft 0.1; implementation in progress.  
**Owner:** Ryan Johnson.  
**Prepared:** October 3, 2026, America/Chicago.  
**Workspace baseline:** Empty directory; no application, selected stack, or Git repository existed when this specification was drafted.  
**Build status (October 4, 2026):** The existing Django implementation now runs locally. The focused engine and runtime checks, a synthetic service pilot, a browser scoring path, and isolated SQLite recovery have passed within their documented limits. R1/R2/R3 gates remain incomplete. See [IMPLEMENTATION.md](IMPLEMENTATION.md) and [roadmap.md](roadmap.md).

**Reading guide:** Start with [release scope](#31-release-scope) and [working assumptions](#21-working-assumptions). The developer contract is in [requirements](#3-requirements), [acceptance criteria](#4-acceptance-criteria-ears-style), and [release gates](#53-release-gates). The [decision register](#7-decisions-and-uncertainties-to-carry-into-planning) collects choices still open before or during planning.

## 1. Goal

Give individuals, clubs, and community organizations an accessible platform to organize, host, promote, and track their own pickleball events, from a casual afternoon tournament to an event operating under an approved sanctioning body's requirements.

The complete experience is: create an event, invite players, fill divisions, check people in, run matches, resolve problems, publish results, and reuse the setup for the next event. An organizer should be able to manage a small event alone without maintaining parallel spreadsheets.

### 1.1 Product principles

- **Useful at a small scale.** A four-court community event is a first-class use case.
- **Low physical and cognitive effort.** Reuse settings, offer sensible defaults, preserve work, and minimize typing. Every primary workflow must support keyboard navigation, voice control, and touch.
- **Organizer control.** Automate routine work and explain decisions. Keep an accessible manual operation available where the event director must make a judgment.
- **Honest status.** Distinguish a proposed schedule from a committed schedule, entered scores from confirmed results, and recorded approval evidence from independent verification.
- **Portable event data.** Organizers can export their information and recover an event without a proprietary ratings or payment service.
- **Rules are versioned.** Tournament format, scoring, eligibility, and sanctioning policies are explicit event inputs, not scattered assumptions.
- **Promotion is part of hosting.** An event page, shareable assets, and useful announcements belong in the core workflow.
- **One maintainable application.** Avoid infrastructure that requires a large operations team.

### 1.2 What success looks like

The first release succeeds when one organizer can run a 32-player doubles event on four courts, including registration, promotion, a waitlist, check-in, scheduling, a withdrawal, a score correction, and final results, with this platform as the event record.

The complete platform succeeds when the same workflow can serve a larger event with approved sanctioned configurations, recorded eligibility checks, officials, financial reconciliation, and accepted external reporting where applicable. Those capabilities are separate release gates; the first release must not advertise them as delivered.

## 2. Constraints and decision boundaries

### 2.1 Working assumptions

These assumptions make the draft concrete. They are proposed product choices, not additional instructions received from Ryan.

| Decision | Draft default | When it must be resolved |
| --- | --- | --- |
| Meaning of “open” | Open source and self-hostable, with a shared hosted deployment possible | Confirm before the implementation plan; the clarification is pending |
| Audience | Individuals, community organizers, and clubs | Established by this specification; no commercial business model is assumed |
| Initial geography | US-oriented examples, English interface, IANA time zones | Before selecting payment and sanctioning integrations |
| Initial ages | Adults 18+; junior registration arrives through a dedicated guardian workflow | Before enabling junior divisions |
| Initial sanctioning target | USA Pickleball as the first candidate adapter | Confirm external requirements before claiming support |
| Initial deployment | Responsive web application; browser installation optional | Architecture selection |
| Initial competition | Fixed singles or doubles entries; round robin and single elimination | R1 scope |
| Initial payments | Free events or organizer-recorded payments collected elsewhere | R1 scope; online collection is R2 |
| Software license | Undecided; source access alone is not an open-source license | Owner selects a license before any open-source distribution claim |
| Revenue model | None specified; no subscriptions, commissions, or platform fees assumed | Only if separately requested |

Do not infer that event participation must be free from the word “open.” Paid events and private club events are compatible with the product goal.

### 2.2 Required technical and operational boundaries

1. The server is authoritative for permissions, capacity, schedules, results, money records, and integration status.
2. Casual operation must work without sanctioning, ratings, maps, SMS, payment, or AI providers.
3. Browser and printed views must remain useful at a venue with unreliable connectivity. R1 does not promise synchronized offline writes.
4. Publishing an event must not publish its participant contacts, private notes, accommodation requests, or approval documents.
5. Public browsing and results viewing must not require an account.
6. A person can participate without creating a reusable platform account; a director can assist them. Identity, permission, and consent requirements still apply.
7. Self-hosting, if confirmed, must support one organization or many organizations with the same code and domain rules.
8. No external approval, membership check, payment success, delivery, rating update, or accepted report may be inferred from a local checkbox or a successful job enqueue.
9. No AI dependency is required for registration, tournament generation, scheduling, score validation, or reporting.
10. The original request delivered this specification only. Ryan’s subsequent request authorized local implementation, resumed October 4 via roadmap.md. Git actions, provider enrollment, messages to governing bodies, deployment and external publication still require explicit delegation.

### 2.3 Meaning of normative language

**SHALL** and **MUST** are acceptance obligations for the release named by the requirement. **SHOULD** is a preferred behavior with a documented reason required for an alternative. **MAY** is optional. A deferred requirement is not silently included in R1.

Unless a paragraph, feature, or section explicitly names R2, R3, or later, its requirements apply to R1. Shared contracts apply when the corresponding feature is introduced: for example, the data model describes all releases but does not require unused finance/provider tables to be built in R1.

Code remains the record of implemented behavior. This file records intended behavior and acceptance. Change the specification before implementing a material scope change, and keep implemented capability claims aligned with verification evidence.

## 3. Requirements

### 3.1 Release scope

The phases below are product boundaries, not an implementation task list or a delivery estimate. R1 is the first complete event workflow. R2 expands operations. R3 adds the externally dependent sanctioned workflow.

| Capability | R1: Community events | R2: Expanded operations | R3: Sanctioned events |
| --- | --- | --- | --- |
| Organizations and event staff | Owner, director, desk, scorer, promotion roles | Additional narrowly scoped grants | Officials and approval-review grants |
| Event creation | Templates, clone event, one venue, multiple days/divisions | Multiple venues, event-series grouping | Versioned sanctioning profiles |
| Participants | Adult singles and fixed doubles, assisted entry | Guardian-managed juniors; partner finder | Governing-body eligibility evidence |
| Formats | Round robin; single elimination | Pools into playoffs; double elimination | Only combinations implemented and approved for the selected profile |
| Scores | Staff-entered game totals, confirmation, corrections | Optional player submissions and disputes | Role restrictions and reporting required by profile |
| Scheduling | Court/time suggestions, conflict checks, manual dispatch | Cross-venue travel and expanded officials assignment | Profile-specific rest and officiating constraints |
| Marketing | Public directory, event page, share links, QR flyer, reusable copy | Opt-in campaigns, sponsor placements, aggregate attribution | Approved sanction marks and references |
| Money | Free entry or external-payment ledger | Optional hosted checkout, refunds, reconciliation | Same money workflow; no automatic financial approval |
| Notifications | In-app status and transactional email | Opt-in marketing email; optional SMS provider | Profile-specific notices and reporting reminders |
| Results | Live board, standings, history, CSV/JSON export | Player history, organizer comparisons, provider-specific exports | Submission packages, acknowledgments, correction reconciliation |
| Connectivity | Online operation, cached public reads, printable recovery pack | Same baseline; any offline write protocol needs a separate spec | Same baseline; no implied offline approval |
| Openness | Portable data and documented setup; license decision pending | Portable integrations | No requirement to surrender event data to a ratings provider |

R1 supported envelope: one venue per event, up to eight courts, eight divisions, 16 entries per division, and 128 unique adult participants per event. An entry is one singles player or one doubles team. The 128-person ceiling applies across divisions, with shared people counted once. These are validation bounds, not minimum event sizes.

R2/R3 target envelope: up to 512 unique participants, 32 courts, and four venues per event. Before lifting R1 limits, verify the larger envelope and define limits for each added format. Unsupported sizes fail with a useful limit message; they must not generate a partial bracket.

### 3.2 Domain vocabulary

| Term | Definition |
| --- | --- |
| Instance | One installation of the platform, possibly serving several organizations |
| Organization | An individual organizer, club, or group that owns events and staff grants |
| Event | The advertised occasion, containing its dates, venue, divisions, policies, and results |
| Division | One competition with its own eligibility, entry capacity, format, scoring, and standings |
| Participant | An event-scoped person who may or may not have an account |
| Account | A reusable authenticated identity; may control its own participant record or authorized dependents |
| Entry | The competing unit in a division: one player or one fixed team |
| Registration | The request, consent, eligibility, and admission history for an entry |
| Team | The fixed membership of a doubles entry in a particular division |
| Stage | One segment of competition, such as a round robin, pool, or playoff |
| Match / game | A match contains one or more games; a result determines match outcome |
| Ruleset | An immutable version of scoring, tie handling, advancement, and eligibility policy |
| Sanctioning profile | A versioned implementation of one body's supported requirements and evidence gates |
| Result revision | An immutable submitted or confirmed version of a match outcome |
| Final results | Results explicitly certified by the event director within this application; external acceptance is separate |

The user interface should say “tournament” where that is clearer, but storage must distinguish the advertised event from its divisions. “Open division,” “open registration,” and “open-source software” are different concepts.

### 3.3 Users and permissions — REQ-ACCESS

Permissions are organization-scoped or event-scoped. Roles are presets over capabilities, not frontend-only labels.

| Role | Allowed responsibilities | Explicit restriction |
| --- | --- | --- |
| Visitor | Discover listed events; view permitted event details and results | No roster contact data or writes |
| Participant / guardian | Manage authorized registrations, consents, preferences, and submissions | No access to another entry's private data |
| Organization owner | Manage organization, grants, all its events, and full exports | Cannot override a governing body's approval |
| Event director | Configure and run assigned events; publish; resolve disputes; finalize | Cannot grant organization ownership |
| Desk operator | View operational roster; register/check in players; manage waitlist within policy | No role management, bulk contact export, or final certification |
| Scorer | View assigned match identities; enter permitted scores | No contacts, money, or unrestricted historical corrections |
| Promotion manager | Edit approved public content; generate share assets | No private roster, accommodation notes, or financial access |
| Finance manager (R2) | Reconcile charges and execute authorized refunds | No competition or sanctioning changes |
| Assigned official (R3) | Officiate assigned matches and record authorized decisions | Access limited to needed match and credential information |
| Instance operator | Operate installation, backups, abuse controls, and account recovery | No implicit application-level participation in every organization |

- Every resource read, mutation, export, background job, and live-update subscription SHALL enforce tenant and role scope.
- Instance operators with infrastructure access can technically access stored data; the UI must not promise cryptographic isolation from the host. Any application support access must be explicit, time-limited, and audited.
- Invitations carry a defined role and scope, expire after seven days, and can be revoked. Redeeming one must not grant broader access.
- Revocation takes effect on the next server request, including active subscriptions. Cached UI state never grants continuing write access.
- The last organization owner cannot remove their own ownership without transferring it. Ownership transfer requires a current authenticated confirmation from both parties.
- Staff authentication SHALL support a non-typing path such as a passkey, plus an accessible recovery method. Optional password entry must support password managers and paste.
- Staff sessions must be established before the event. A mail outage must not invalidate an otherwise valid signed-in desk session.
- Short match codes are navigation aids only. A code such as `M-042` never authorizes a score change.

### 3.4 Primary journeys — REQ-JOURNEY

**Casual organizer:** Choose a template; set title, date/time zone, venue/courts, division format, and capacity; preview; publish; share a link or flyer; review registration; print a desk pack; check players in; assign matches; enter results; certify standings; clone the event later.

**Player:** Open an event link; see when and where to attend, total price, format, eligibility, cancellation policy, and accessibility details; choose a division; register alone or with a partner; accept applicable policies; receive a clear admission or waitlist status; find check-in and next-match information; view results.

**Desk volunteer:** Open the assigned event; search by display name or scan a registration token; see only relevant eligibility/payment blockers; check in; find the next ready match; assign a court; enter or review scores without navigating a dense administration area.

**Spectator:** Open a read-only event board without an account; find a player, division, court, match, or results; see whether information is live, delayed, or final.

**Sanctioned director (R3):** Select a supported body/profile; record an application and approval evidence; complete eligibility and event requirements; resolve blocking issues; publish accurate status; run approved competition; review the reporting package; authorize submission; track acceptance and corrections.

### 3.5 Event setup and lifecycle — REQ-EVENT

1. An organizer SHALL create an organization with only a display name and contact route; legal-business fields are not required for a free casual event.
2. Templates SHALL include “Small doubles round robin,” “Singles elimination,” and “Blank event.” Defaults must be visible and editable before publication.
3. The event SHALL store title, slug, summary, organizer identity, contact route, visibility, time zone, dates, venue, courts, accessibility information, policies, divisions, and public assets.
4. Drafts autosave with visible saved/pending/error states. A failed save must not display “Saved.” Offer retry without retyping.
5. Publication SHALL require a valid date range, time zone, venue instructions, organizer contact, at least one supported division, admission dates, participation policy, price/refund information, and complete competition settings.
6. Visibility SHALL be `public`, `unlisted`, or `private`. Public events appear in the instance directory; unlisted events are accessible by URL and omitted from discovery/indexing; private events require an access grant. An unlisted link is not a privacy barrier.
7. Registration opening and closing are independent of event publication and competition state. Closing registration does not cancel the event.
8. A date, venue, price, eligibility, roster, or competition-policy change after publication SHALL create a revision and identify affected registrants. Material changes require a director-reviewed participant notice.
9. Existing orders retain their quoted prices and refund-policy versions. A later price edit cannot silently change an accepted registration.
10. Cloning SHALL copy settings and permitted owned artwork into a draft. It SHALL exclude registrations, contacts, consents, results, payment records, sanction evidence, and external submission IDs.
11. Cancellation SHALL require a reason and preview of affected entries, notices, and unsettled finances. It freezes new registration and match starts; it does not pretend refunds have completed.
12. Archiving SHALL make an event read-only except approved privacy, finance, and correction workflows. Archiving is distinct from deletion.
13. Event and division settings SHALL display a plain-language summary before publication: who can enter, how many matches to expect, how winners are decided, and what happens on withdrawal.
14. Division merging or splitting after publication SHALL be an explicit migration with a roster, eligibility, price, and schedule preview. R1 supports transfers before draw lock; automatic merges and splits are deferred to R2.

### 3.6 Venue, courts, and accommodations — REQ-VENUE

- Store venue address or precise arrival instructions, optional coordinates, parking, restrooms, contact, and indoor/outdoor designation. Maps are optional enhancements; text directions must remain available.
- Courts have a stable ID, human-readable label, availability intervals, accessibility notes, and operational status: available, occupied, blocked, or closed.
- Setup time, lunch breaks, venue closing time, lighting limits, and weather blocks are scheduling inputs.
- Record venue accessibility as organizer-provided information: step-free routes, seating/rest areas, accessible restrooms, surface notes, and how to request assistance. Use “unknown” where not supplied; do not infer accessibility from a checkbox.
- A private accommodation request SHALL capture what support is needed, not require a medical diagnosis. Show it only to specifically authorized operations staff.
- Support court preferences and additional rest requirements as explicit scheduling constraints. Do not display the reason on public match boards.
- R1 supports participants with accommodation needs in its supported formats. Specialized wheelchair/adaptive competition rules require a tested profile before being offered as such.
- Venue safety decisions remain with event staff. The platform records holds, notices, and operational decisions; it does not decide whether conditions are medically or physically safe.

### 3.7 Divisions and eligibility — REQ-DIVISION

A division SHALL define singles/doubles, entry capacity, registration window, format, scoring profile, eligibility policy, seeding policy, minimum entries, and schedule window.

Eligibility fields MAY include age range, competition category, skill band, membership, and rating source. Every constraint must explain its basis and validation state. R1 permits organizer-defined adult categories; it does not label them as sanctioned categories.

- Age eligibility uses a declared reference date. R1 defaults to the event start date. Age 18+ is required on that date; any required birth date remains private.
- Skill bands use explicit inclusive/exclusive boundaries. A value exactly on a boundary must have one documented result, not vary by client.
- Self-reported skill, organizer-assessed skill, and provider-verified rating are different records with provenance and observed timestamps.
- Each rating snapshot identifies provider, discipline, value or unrated state, verification method, and freshness. Missing or failed verification is `unknown`, not eligible.
- Doubles eligibility SHALL state how partners' skills are combined. R1 default: use the higher self-reported/approved skill value; do not average silently.
- Eligibility for identity-related categories SHALL follow the event's declared policy; never infer identity from names, photographs, or account metadata.
- Playing in more than one division is allowed only when the event permits it. Conflicts are detected across the individual participants in all their entries.
- A director may grant a documented casual eligibility exception. The UI shows its scope and reason. An exception cannot manufacture external eligibility or approval.
- Registration SHALL disclose expected public identification. Allow a casual event display name or alias, while keeping required private identity fields separate.

### 3.8 Registration, partners, and capacity — REQ-REG

The admission unit is an **entry**. Singles capacity counts people; doubles capacity counts teams. Display both teams and people so “16 spots” is never ambiguous.

**Entry paths:** self-registration through a verified email link, existing-account registration, director-assisted entry, or roster CSV import with preview. A reusable account is optional. A verified manage-registration link grants access only to that registration and expires; it is not a staff credential.

1. A player can be active in at most one entry per division. Enforce this with server-side identity and uniqueness checks, not name comparison alone.
2. Doubles registration identifies both people. Each adult accepts their own participation terms; a captain cannot silently consent for a partner.
3. A partner invitation creates an incomplete entry, not a confirmed team. R1 does not hold capacity while waiting for a partner; say this before invitation. Once complete, the team competes for a spot atomically.
4. Reusing a partner's contact for an invitation does not enroll that person in marketing or other events. Invitations must have resend limits and an abuse-report route.
5. R1 confirms eligible free entries immediately when capacity exists. For organizer-collected fees, the event chooses whether an unpaid entry is admitted or awaits the desk; show this policy before signup.
6. Capacity SHALL count admitted entries plus unexpired reservation holds. Incomplete entries and ordinary waitlist entries do not consume a spot.
7. Acquiring capacity, changing admission status, and issuing a hold SHALL be atomic. Two requests for the last spot cannot both succeed.
8. A division at capacity SHALL offer a waitlist when enabled. Record a monotonically ordered queue position at the time the entry becomes complete and eligible.
9. A released spot offers the earliest eligible waitlisted entry a reservation. Default expiry is 24 hours, shortened to registration close if earlier. Display the actual deadline and event time zone.
10. A waitlist offer occupies one spot until accepted, declined, or expired. Reminder delivery failure does not extend it silently. Expired offers advance once through an idempotent operation.
11. A director can reorder or skip a waitlist entry only with a recorded reason. Notify the affected entry without exposing anyone else's private details.
12. R2 payment checkout reserves capacity for ten minutes, bounded by registration close; authoritative server time controls expiry. A late payment success is reconciled explicitly instead of overselling.
13. Withdrawal releases admission under the applicable policy. It does not erase consent, played results, payment history, or audit evidence.
14. A partner substitution before draw lock requires the replacement's acceptance and eligibility check. After draw lock, ordinary edits are blocked; the director follows the withdrawal/exception procedure and the relevant ruleset.
15. R1 “need a partner” is an expression of interest with a director contact route, separate from admitted entries. R2 may provide opt-in partner discovery without exposing contacts publicly.
16. Desk-created people get event-local participant IDs. Linking or merging them with an account requires verified ownership or director-reviewed evidence. Never merge people solely because their names match.
17. CSV import SHALL provide a sample template, row-specific errors, duplicate candidates, and a no-write preview. The final import is atomic for accepted rows and produces a report; no notifications are sent until the director authorizes them.
18. Assisted registration SHALL distinguish staff-recorded consent from participant acceptance. An unresolved required consent blocks check-in/competition; it must not be marked accepted by default.

An event may support an accessible assisted-acceptance method where its participation policy allows it, such as reading terms aloud and recording the participant's explicit verbal acceptance. Capture the exact policy version, method, actor, participant, and time; do not label the record as the participant's electronic signature. Required external consent procedures still govern their own profiles.

### 3.9 Check-in and no-shows — REQ-CHECKIN

- Check-in is a separate status per participant and division/day as required; it does not alter eligibility or payment evidence.
- A doubles entry is ready only when both partners are checked in and all required blockers are resolved.
- Staff can find entries by name, entry code, or an optional QR scan. Every scanning workflow has a manual lookup alternative.
- A QR token must be opaque, scoped, and revocable. It cannot contain contact details or grant score-edit access.
- Walk-up registration follows the same capacity, policy, consent, and identity checks as online registration.
- The dashboard lists expected, checked-in, late, withdrawn, and blocked participants with the next action.
- A no-show timer starts only from a recorded call-to-court action and the configured grace period. R1 never auto-forfeits; a director confirms the outcome.
- Repeated check-in commands are idempotent. Staff can undo a mistaken check-in with an audit record.
- The printed desk roster omits unnecessary sensitive data and clearly identifies its generation time and schedule revision.

### 3.10 Formats, draw generation, and advancement — REQ-FORMAT

All generators take a frozen eligible-entry list, ruleset version, seed order/random seed, and configuration hash. The same inputs SHALL produce the same draw. Previewing a draw must not publish or start matches.

| Format | Required behavior | Release |
| --- | --- | --- |
| Single round robin | Every unordered pair meets exactly once; odd counts create rest rounds, not wins | R1 |
| Single elimination | One loss eliminates; byes do not count as played matches; one championship winner | R1 |
| Pools into playoffs | Round-robin pools followed by an explicitly mapped playoff; qualification is explainable | R2 |
| Double elimination | Explicit winner/loser paths, loss counts, and championship/reset policy | R2 |
| Rotating partners, ladder, Swiss, team league | Separate future specifications required | Later |

**R1 round robin:** support 2–16 entries. Generate `n × (n − 1) / 2` matches. Even `n` uses `n − 1` rounds; odd `n` uses `n` rounds with one rest entry per round. A round is a grouping constraint, not proof that enough courts exist. A participant must never appear twice in a round.

**R1 single elimination:** support 2–16 entries. Seed into the next power-of-two draw. Generate bracket seed positions recursively: start `[1, 2]`; to expand from size `k` to `2k`, replace each seed `s` with `[s, 2k + 1 − s]`. Absent seeds become byes. Propagate byes without inventing scores. With no withdrawals, exactly `n − 1` played match results determine the champion. R1 awards first and second; a bronze playoff or other placement bracket belongs to R2.

**Seeding:** R1 permits an explicit director seed order or a saved random permutation. Show the order and method before draw lock. A later rating update cannot silently reseed the draw. R2 may suggest seeds from an eligible rating snapshot; the director reviews the proposal.

**Locking:** Closing entry admission and locking the draw are separate actions. Generating from an unlocked roster is provisional. Publication locks the draw revision. Before any match starts, a director can replace it through a previewed regeneration that preserves the old revision and invalidates old assignments and links safely. After play starts, the draw cannot be regenerated wholesale.

**R2 pool default:** distribute seed order in a snake across pools; pool sizes differ by at most one. The organizer chooses a fixed number `q` advancing from every pool. Playoff qualification is blocked until every relevant pool is complete and certified. Order qualifiers by finish place, then an explicit prepublished pool order; place seeds with the elimination algorithm. Do not compare raw point totals across unequal pool sizes or promise rematch avoidance. Alternative qualification mappings need their own tested preset.

**R2 double elimination:** a profile must define every loss destination, bye effect, withdrawal effect, and final reset. Default true double elimination includes a reset match if the previously undefeated finalist receives their first loss. A single-final variation must have its own name and disclosed policy. A generic “double elimination” label cannot hide a different loss rule.

### 3.11 Scoring, standings, and corrections — REQ-SCORE

**R1 casual scoring profiles:** side-out scoring, one game or best of three, target 11, 15, or 21, win by two, no cap. Default is one game to 11. These are product-supported casual combinations; they are not a claim that every combination is allowed at a sanctioned event. Rally scoring and point-by-point officiating are outside R1.

The system records game totals, not the service sequence. It cannot establish whether rallies were officiated correctly from final scores.

For a normally completed game with target `T`, let `W` and `L` be the winner's and loser's totals. Scores must be nonnegative integers, `W > L`, and either `(W = T and L <= T − 2)` or `(W > T and W − L = 2)`. Thus 11–9 and 12–10 are valid for target 11; 11–10 and 12–8 are invalid final totals. A match ends when a side has the required game wins; extra games after that point are rejected.

- Outcome types SHALL distinguish played completion, retirement after play started, walkover before play, disqualification, void, and unresolved. A bye is an advancement condition, not a result against an invented opponent.
- Preserve actual played game scores on retirement. Record an incomplete game separately from completed games. Do not manufacture 11–0 games to make an administrative outcome fit the schema.
- Every entered result starts as a submission. Authorized staff confirm it after a summary naming both sides, game totals, and the resulting winner. R1 permits one staff member to submit and confirm, but records both actions.
- A match result becomes authoritative only after the server commits the confirmation. Standings, advancement, and notifications derive from that committed revision.
- R2 player submissions require the event's chosen confirmation policy: opponent agreement or authorized staff confirmation. Silence never confirms a disputed result automatically.

**R1 round-robin ranking:** rank by confirmed match wins. For a tied group, use: (1) wins in matches within that original tied group, but only if all its pairwise matches completed normally; otherwise skip that criterion for the whole group; (2) overall point differential from normally completed matches; (3) total points scored in those matches; (4) original published seed order. Apply criteria once, lexicographically, without recursively recalculating head-to-head for smaller subgroups. Show which criterion broke the tie. Byes, walkovers, disqualifications, and retirements contribute no points to these calculations; an administrative winner still receives a match win. This is an explicit casual preset, not an external rulebook implementation.

Standings remain provisional until every scheduled match is resolved. If the event cannot complete its schedule, display partial standings without awarding a final rank through this preset; the director either completes the schedule or publishes a separately identified partial-results report.

**Withdrawal after draw lock:** preserve played results. Future elimination matches become documented walkovers. In round robin, future opponents receive a documented walkover win under the published casual preset. No-show and disqualification decisions use explicit outcome records and reasons. A profile with a different withdrawal policy must implement it separately.

**Corrections:**

1. A confirmed result is never overwritten in place. Create a proposed replacement with a reason, actor, expected revision, and affected-match preview.
2. If no affected downstream match has started, confirming the correction atomically supersedes the result, updates advancement, clears stale assignments/calls, recomputes standings, and notifies affected participants.
3. If an affected downstream match has started, reject an ordinary correction and open a director incident. R1 freezes the affected branch. The director can void affected started/completed descendants in reverse dependency order, preserving their evidence, then apply the source correction and reschedule replacements. If replay is impossible, publish partial results; do not silently keep incompatible winners.
4. A correction after final certification reopens the affected division with a public “results under correction” notice. A new certification produces a new results version.
5. External submissions derived from a superseded revision become `correction_required`, even if previously accepted. Provider support for corrections determines the next action; local edits alone cannot resolve external state.

### 3.12 Scheduling and match-day operation — REQ-SCHEDULE

The scheduler suggests an understandable feasible schedule. It does not promise a globally optimal schedule or exact finish times.

**Hard constraints:** court availability, one active match per court, one active match per person across all divisions, resolved bracket dependencies, entry readiness, declared participant unavailability, minimum rest, and any required assigned official. R2 adds travel time between venues. A court's venue time zone is the event time zone in R1.

**Soft preferences:** minimize idle courts, reduce long waits, group divisions, honor preferred times/courts, and keep estimated finish within the venue window. The UI must distinguish a preference from a hard restriction.

1. Use a director-editable estimated match duration, default 25 minutes, and turnaround buffer, default five minutes. These are planning assumptions, not promises.
2. Casual minimum rest defaults to ten minutes from actual match completion. Per-person accommodations may increase it. No implicit override is allowed; changing the policy requires a recorded director action, and externally required minima cannot be relaxed locally.
3. Show total expected matches, estimated court-minutes, available court-minutes, and obvious infeasibility before draw publication. A capacity estimate is not a guarantee that every constraint can be satisfied.
4. Generate a proposed schedule using a deterministic priority order: earliest allowed start, dependency readiness, published division order, match ID. Return unscheduled matches with specific blocking constraints rather than placing conflicts.
5. Persist scheduled intervals as half-open intervals `[start, end)`. Buffer and rest extend the relevant occupied intervals. Adjacency is allowed only after those constraints are satisfied.
6. Committing or editing a schedule revalidates the expected event revision and every hard constraint in one transaction. Two staff members cannot reserve the same court concurrently.
7. Before calling or starting a match, recheck actual court, player, rest, check-in, and official readiness. A call atomically reserves the involved people and court until recalled, started, or resolved; two simultaneous calls cannot claim the same person. An optimistic estimated end time never releases an active player or court.
8. The desk board SHALL show available courts, ready matches, matches waiting for a dependency/person/rest, delayed matches, and unscheduled matches. Every move has a button/menu alternative to drag-and-drop.
9. A director can pin a match to a time/court; regeneration preserves valid pins and explains invalid ones. It must not silently move a called or started match.
10. Distinguish planned start, earliest start, called time, actual start, actual end, and court release. Store the actor for manual time corrections.
11. A weather/venue hold can cover an event, court group, or court. It blocks new starts. For a suspended active match, record whether the court remains occupied and retain its existing scores.
12. Resuming proposes a revised schedule; affected players see the new revision and receive an operational notice. If no feasible schedule exists, staff see choices such as extending the window or postponing matches. The scheduler never changes scoring rules to force a fit.
13. An organizer may change an unstarted casual stage's scoring policy through an explicit revision and notice. Started matches retain their original profile; a sanctioned profile controls whether any change is permitted.
14. R1 public updates use event revision numbers and a last-updated time. On reconnect or a revision gap, clients fetch a fresh snapshot before applying more updates.
15. Duplicate start/end/call commands must not create duplicate outcomes or messages.

### 3.13 Discovery, event pages, and marketing — REQ-MARKET

**R1 event discovery:** search public events by title, organizer, location text, date range, singles/doubles, skill band, admission status, and casual/sanctioning status. Do not require location permission. Start with a list; a map is optional. Sort choices include soonest and recently published.

**Event page:** clear title, organizer, date and event time zone, venue/directions, divisions, capacities, entry price, policy summary, accessibility details, contact route, registration action, announcements, schedule, and results. Show whether divisions are open, full, waitlisted, or closed. Public display must use the same authoritative data as registration.

- An organizer SHALL preview the public page without publishing it. Draft preview URLs require authorization and must not enter search indexes.
- Public pages SHALL expose useful titles, descriptions, social preview metadata, canonical URLs, and structured event information derived from actual publication state.
- R1 SHALL generate an accessible print page/flyer, a QR code with a human-readable URL, and reusable short invitation/reminder copy. QR links lead to the event page, never directly authorize registration or payment.
- Text on generated materials SHALL come from current event data. Include the asset revision/date so a changed venue or cancellation can be recognized. The event page remains the current source.
- Sharing opens the user's chosen sharing workflow or copies approved text; it does not automatically post to social accounts.
- Allow organizer-supplied logos and hero images, with required alternative text where informative. Text-only pages must look complete. Do not require an image generator.
- Sponsors (R2) are optional named placements with logo, link, and placement dates; participant information is not included in a sponsor package.
- Tracked links (R2) use an allowlisted campaign identifier. Report aggregate views and completed registrations with a documented attribution window. Describe counts as estimates; do not claim causal attribution or unique people from pageviews.
- Marketing email (R2) requires separate explicit consent, a recipient preview, unsubscribe controls, suppression handling, and a send confirmation. Event registration cannot silently subscribe a person to future events.
- Imported contacts are not a marketing audience unless their consent and source are recorded.
- No advertising purchase, social auto-posting, scraping, direct-message outreach, or AI-generated testimonials are required.

### 3.14 Notifications and communications — REQ-NOTIFY

| Notice | Trigger | Default audience | Release |
| --- | --- | --- | --- |
| Registration status | Admission, waitlist, partner action, or withdrawal | Affected participant(s) | R1 |
| Waitlist offer | Capacity reserved for an entry | Invited entry | R1 |
| Event change/cancellation | Director confirms a material update | Affected registered entries | R1 |
| Check-in and arrival instructions | Director-approved scheduled notice | Admitted participants | R1 |
| Court call or schedule change | Committed dispatch/revision | Affected participants with opted-in delivery | R1 in-app/email |
| Results published/corrected | Director certification or correction | Relevant participants | R1 |
| Promotion | Organizer-approved campaign | Consenting subscribers | R2 |
| Report action required | Failed/rejected/unknown submission | Authorized director | R3 |

- Use an outbox record written in the same transaction as the triggering change. A worker delivers it after commit.
- Track queued, sending, provider-accepted, delivered where proven, bounced, failed, and suppressed states. Provider acceptance is not proof that a human received the message.
- De-duplicate by event revision, notice type, recipient, and channel. Retrying a failed job must not intentionally send duplicate invitations or calls.
- Participants can select channels and disable nonessential notices. Marketing suppression cannot be bypassed by changing a campaign's label to “transactional.”
- The event board remains the operational source when delivery is unavailable. Staff see failed essential notices and an alternative contact action.
- Email addresses and phone numbers must not appear in group recipient lists. Notification links must not leak private state through preview images or analytics.
- SMS is optional in R2, off by default, with explicit consent and organizer-visible estimated cost before bulk sending. No automated emergency-dispatch claims.
- R1 contact is a protected organizer contact route or disclosed organizer email. A public participant-to-participant chat system is not required.

### 3.15 Fees, payments, and refunds — REQ-MONEY

**R1:** An event is free or has a disclosed fee collected by the organizer outside the application. Record the amount due, currency, payer, payment method label, reference, amount received, and recording staff member. “Recorded as paid by staff” is distinct from “confirmed by payment provider.” A pay-at-check-in event must state whether unpaid entries retain their place.

**R2:** Optional online checkout is implemented through a provider adapter. Before enabling it, the deployment must identify the payment recipient, account ownership, supported currency, fees, refund behavior, and who handles disputes. A fee-taking marketplace arrangement is a separate owner decision; it is not assumed here.

1. Store monetary values in integer minor units with an explicit currency. No floating-point totals, cross-currency totals, or automatic currency conversion.
2. R1/R2 support one currency per event. The initial proposed currency is USD. Enabling another currency requires the adapter to implement its minor-unit and refund behavior.
3. Display an itemized total before acceptance: event entry, division charges, discounts if supported, and any applicable taxes/provider charges. The quoted order is immutable after confirmation.
4. R2 uses one payer per entry/order initially. Split payments, installment plans, merchandise, prize payouts, and multi-organizer fund splits are outside these releases.
5. Use provider-hosted payment collection. Card details must never enter application storage, logs, or analytics.
6. A browser return URL is not proof of payment. Only verified provider evidence or an explicitly labeled manual receipt changes the ledger.
7. Webhooks SHALL be authenticated and deduplicated. Out-of-order notifications must not revert a completed refund or duplicate a paid admission.
8. After a checkout reservation expires, a late success SHALL first check whether capacity can still be acquired atomically. If it cannot, record `paid_without_admission`, notify finance staff, and offer the declared refund/resolution path. Never silently add an extra team.
9. Refund requests, provider submission, provider acceptance, and final settlement are separate states. Repeated clicks cannot produce duplicate refunds.
10. Refunds cannot exceed the unrefunded captured amount. Partial refunds identify the affected line items; a withdrawal and a refund are related but independent operations.
11. Cancellation SHALL create a reviewable refund queue according to each accepted policy. It must not claim money was returned when only a queue item exists.
12. Reconciliation SHALL surface provider/local mismatches, unknown outcomes, chargebacks, and aged pending items. Retrying an unknown charge/refund first checks the provider's existing operation by idempotency/reference.
13. A finance export separates amounts charged, actually received, fees, refunds, and unresolved balances. It is an operational ledger, not a tax-filing product.

### 3.16 Sanctioning profiles and external evidence — REQ-SANCTION

The platform SHALL distinguish three independent facts: the competition rules selected, the event's external approval status, and this software's eligibility to serve that event. Passing an internal checklist establishes only that the modeled checks passed.

**Research boundary:** On October 3, 2026, USA Pickleball's sanctioning page described Standard, Medal Match Plus, and No-Referee sanctioning, eligible membership tiers, and approved software providers. The product implication is a gate for confirming software eligibility as well as event approval. This specification does not establish approval for this project. See [USA Pickleball sanctioning](https://usapickleball.org/sanctioning/).

The current rules page links the 2026 rulebook. A formats guidance page still contains 2025-specific language. Therefore a production profile must resolve the applicable edition, effective dates, and conflicts against authoritative requirements before activation; copying a web page is insufficient. See [official rulebook index](https://usapickleball.org/rules/) and [formats guidance](https://usapickleball.org/sanctioning/formats/).

**Profile contract:**

- Body identifier, jurisdiction, profile name/version, rulebook edition, effective interval, source references, source content hashes where permitted, review timestamp, and reviewer.
- Supported sanction categories, divisions, formats, scoring combinations, tie rules, withdrawal/retirement treatment, rest rules, official requirements, and report schema.
- Membership/rating evidence requirements, expiry rules, equipment attestation requirements, event documents, and pre-event/post-event deadlines.
- A machine-checkable capability list. Any unsupported required rule blocks that combination rather than falling back to the casual preset.
- Review status and a mandatory `review_due_at`. A profile cannot be newly selected after its review due date; existing events receive a review-required flag. A new rule edition never silently changes an already started match.
- Profile data is declarative and validated. Arbitrary organizer-uploaded executable rule code is outside scope.

**Event evidence contract:** Store application reference, sanction identifier, coverage dates/scope, evidence source, attachment or public verification URL, reviewer, verification method, verification time, and any expiry/revocation. Private documents remain private.

Use explicit states: `not_requested`, `preparing`, `submitted`, `approved_recorded`, `approved_verified`, `rejected`, `expired`, `revoked`, and `review_required`. `approved_recorded` means a director supplied evidence; it does not mean an external service verified it. A self-hosted instance's reviewer is not an independent certifying authority.

**Public display:** R1/R2 make no sanctioned-operation claim. R3 can show “Approval recorded: [body]” with its evidence method, or “Approval verified: [body]” with verification basis, only when the profile and software eligibility gates also pass. A pending application displays “Sanctioning pending.” Public filters must not mix pending, recorded, and verified status. Branding requires documented permission; a software-generated badge cannot stand in for a body's mark.

**Workflow requirements:**

1. Selecting sanctioned mode SHALL expose the exact implemented profile and unresolved blockers before registration publication.
2. Eligibility checks SHALL record member/rating identifier, required validity date, observed state, source, and check time. A timeout becomes unknown; a director cannot mark a provider outage as a successful verification.
3. Where a profile permits manual evidence review, record the document and review method. Where it requires a live provider result, missing access is a blocking dependency.
4. An official assignment SHALL check the credential evidence required by the profile and schedule availability. A job title alone is not a credential.
5. Membership changes, revoked approval, changed event dates, or changed rules SHALL trigger reevaluation and a visible action item. They cannot silently remain green.
6. A sanctioned division SHALL never use the casual ranking/withdrawal defaults merely because a profile implementation is missing.
7. The director SHALL preview a report package including IDs, divisions, draw/results revisions, required participant fields, exceptions, and omissions before authorizing submission.
8. Reporting SHALL distinguish generated, authorized, queued, sent, acknowledged, accepted, rejected, outcome-unknown, and correction-required states. A file download is only generated; email delivery is not report acceptance.
9. Manual submission MAY satisfy a profile only when the receiving body's permitted process allows it. Record destination, submitted package hash, actor, date, and acknowledgment evidence.
10. Automatic submission SHALL use a documented authorized integration; no scraping of logged-in portals or assumed private endpoints.
11. A final local result revision SHALL remain traceable to every package that included it. Corrections create a superseding report or an explicit unresolved external discrepancy.
12. R3 release requires an approved supported workflow and realistic end-to-end evidence. Fixtures alone cannot establish governing-body acceptance.

The first R3 profile must enumerate the subset actually supported. Junior, adaptive, specialized team, or rally formats remain disabled for sanctioned use until their specific rules and reports are implemented. Other governing bodies can be added through the same contract; US requirements are not treated as universal.

### 3.17 Ratings and integration adapters — REQ-INTEGRATION

Casual events work without a rating. A platform-local match history is not an official rating or national qualification record.

DUPR's club resources describe partner integrations and manual result upload routes. That establishes candidate integration paths, not this project's API access or permission. See [DUPR club resources](https://www.dupr.com/club-resources).

Each ratings adapter SHALL expose capability flags for identity lookup, rating fetch, result submission, status lookup, correction, and deletion. Unsupported operations stay visibly unavailable.

- Persist external identity links only after verification or explicit manual evidence review. Names alone are insufficient identity keys.
- Preserve separate disciplines and provider definitions. Do not combine different rating systems into one implied comparable value.
- Store the rating snapshot used for eligibility/seeding. Later provider changes do not rewrite the historical basis.
- Export only accepted, consented, provider-supported data; exclude byes and fabricated administrative game scores. Explain skipped results.
- Retry rate-limited/temporary failures with bounded backoff; use a dead-letter/action-required state after the documented attempt limit.
- A retry uses the same idempotency key and payload hash for the same result revision. A correction has a new revision and links the prior external record.
- If a provider lacks idempotency or status lookup, an ambiguous response stops automatic retry until reconciliation prevents a duplicate.
- Provider-specific CSVs require a versioned mapping, exact field validation, and an export manifest. A generic CSV must not be labeled import-ready for an unverified provider format.
- Disconnecting a provider stops future jobs and revokes stored credentials where supported. It does not claim external records were removed.
- Credentials belong to the applicable instance or organization and cannot cross tenants. Exports omit secrets.

### 3.18 Junior participation and personal data — REQ-PRIVACY

R1 SHALL reject under-18 registrations under the event's age-reference rule. It must not accidentally enable minors through imports or assisted entry. R2 introduces a separate guardian-managed flow before junior divisions are enabled.

R2 SHALL record guardian identity, authority/consent evidence appropriate to the deployment, the dependent relationship, approved communications route, and required participation acceptance. Junior public display defaults to a limited display name and division; full birth dates, contacts, and detailed future locations are never exposed through a public participant profile. Adults cannot directly message a junior through the platform.

**Visibility classes:** public event data; participant-visible self/entry data; operations-only data; finance-only data; and restricted documents/credentials. Every field and export must have a declared class. A serializer built for staff use must not be reused as the public API response.

- Collect only the information needed by the selected event/profile. Phone, birth date, emergency contact, gender-related category information, and provider IDs are not universally required.
- Required participation acceptance, optional photo permission, marketing consent, and provider-result sharing must be separate versioned records.
- Public player history is opt-in for adults. An event's published result disclosure is separate from a reusable public profile and appears before registration.
- Provide data access/correction and deletion-request workflows with identity checks. Explain which records can be deleted, deidentified, or retained for a documented purpose.
- Keep sensitive values out of immutable audit payloads; refer to controlled records by ID. Deidentification can remove the mapping while preserving the competition/financial event that occurred.
- Proposed retention defaults: purge expired login/manage tokens promptly; purge unused partner invitations after 30 days; delete accommodation and emergency-contact details 30 days after event completion; retain ordinary operational contacts for 12 months unless a separately consented ongoing relationship exists.
- Consent, payment, incident, and sanction-document retention must have a deployment policy before the relevant feature is enabled. This specification does not invent a universal legal retention period. Retention holds require a reason, owner, scope, and review date.
- Privacy deletion must invalidate generated private exports/caches and propagate through the documented backup retention window. Public result deidentification must also update search projections and public feeds controlled by the instance.
- Uploads and exports SHALL have access checks, expiry where applicable, and revocation. Download URLs are not permanent public links.
- A self-hosted deployment identifies its operator and privacy/contact policy. This does not require a commercial company structure.

### 3.19 Dashboards, reports, and portable data — REQ-REPORT

**Organizer dashboard:** upcoming events, admission counts, incomplete entries, waitlist, payment balances, readiness blockers, active courts, delays, unresolved scores, and unsent notices. Rank actionable problems ahead of decorative charts.

**Player view:** entry status, partner status, balance, required actions, check-in instructions, next match, schedule revision, and results. “No next match yet” must explain whether the player is waiting for a result, schedule, partner, or director action.

**Public board:** division selector, searchable display names, court status, match list, textual bracket alternative, standings, and last-update age. Optional full-screen display mode uses the same privacy policy.

**Exports:**

- Public results CSV with display names, division, placement/status, match outcome, and game totals where appropriate.
- Authorized operational roster CSV with a field-selection preview; private fields are excluded by default.
- Versioned JSON event archive including configuration, participants within authorization scope, entries, draws, revisions, results, consents, and audit references. Exclude credentials and live auth tokens.
- Manifest with schema version, export time, event revision, file hashes, and redaction information.
- Human-readable printable schedules, scoresheets, check-in sheets, and current results; no external PDF service required.
- R2 finance report and optional cross-event aggregate participation/registration trends.
- R3 body/provider packages generated through the corresponding verified schema adapter.

A full authorized archive SHALL be importable into a compatible clean installation through a dry run and conflict preview. Remap instance-local IDs consistently; invalidate authorization tokens, remap/review staff ownership, and disable all notification/payment/submission jobs by default. Importing old sanction evidence preserves provenance and historical status without reasserting current verification. A portable archive and an infrastructure backup solve different recovery problems.

Metric definitions SHALL be explicit: unique people, admitted entries, team count, checked-in people, completed matches, and paid orders are different measures. Cancellation and withdrawal must not disappear from historical totals. No cross-instance public rankings are inferred from incomplete imported data.

### 3.20 Accessible interaction and page inventory — REQ-UX

Target WCAG 2.2 AA for the implemented web experience. Treat conformance as an evaluation outcome supported by evidence; automated checks alone do not establish it. See [W3C WCAG 2.2](https://www.w3.org/TR/WCAG22/). The following are product-specific interaction requirements in addition to that target.

- Primary actions use generous controls; aim for at least 44 by 44 CSS pixels for check-in, court assignment, and score entry. Small-screen operation must not depend on precise dragging.
- Accessible names include visible labels so voice commands can target controls. Use consistent names such as “Check in,” “Assign court,” and “Confirm score.”
- Provide autocomplete, previously used settings, event cloning, bulk actions with previews, and short match/entry codes. Do not require repetitive copying or retyping.
- Keyboard shortcuts are optional, discoverable, disableable, and inactive while typing in fields. A command/search action can jump to a player, match, or court.
- Buttons and menus provide alternatives to scanning, dragging, maps, hover, color, and gestures. Text descriptions accompany bracket graphics.
- Score entry uses large numeric inputs/steppers, explicitly names both sides, preserves entry on validation failure, and offers an undoable draft before confirmation.
- Live updates preserve focus and scroll position, announce useful status without constant interruption, and can be paused. A refresh cannot close an active score-entry form.
- Reauthentication preserves unsent form content where safe. Time-limited reservations show remaining time and an accessible explanation of what expiry does.
- Narrow layouts, zoom, reduced motion, high-contrast presentation, and screen readers must be considered in the core pages. No full-page horizontal scrolling at a 320 CSS-pixel viewport; bracket visualizations may scroll within a labeled region and must have an equivalent list.
- Error messages identify the field/problem and next step. A retry should reuse existing input. Do not show raw stack traces, schema names, or provider payloads in player workflows.

| Surface | Required pages/views |
| --- | --- |
| Public | Event directory, event details, division/draw, schedule/live board, results, organizer page |
| Participant | Registration, partner acceptance, manage entry, my event status, notification preferences |
| Organizer | Organization/events, setup wizard, publication preview, divisions, roster/waitlist, communication preview |
| Event desk | Check-in, courts and ready queue, match detail/score entry, holds, incident/correction view |
| Reporting | Finalization review, exports, archive/import status |
| R2 additions | Payments/refunds, campaign audience, guardian/dependent management, provider mappings |
| R3 additions | Profile/evidence checklist, officials, reporting packages, external reconciliation |

### 3.21 Data model and invariants — REQ-DATA

The storage model SHALL represent the following concepts; exact table names and framework models are selected in the implementation plan. Child records need enforceable tenant lineage even where the physical schema derives it through a parent.

| Entity group | Core records and required attributes |
| --- | --- |
| Identity/access | Account, organization, role grant, scoped invitation, session/recovery credential |
| Event configuration | Event revision, venue, court, availability interval, division, immutable ruleset/profile version |
| Participation | Event participant, optional account/guardian link, entry, entry member, registration, capacity reservation, waitlist offer |
| Evidence | Consent version/acceptance, eligibility snapshot, private accommodation, external identity/rating snapshot |
| Competition | Stage, draw revision, seed order, match, match-slot dependency, schedule assignment, check-in, official assignment |
| Results | Submission, game score, outcome, immutable confirmed revision, correction incident, standings/finalization snapshot |
| Money | Price/policy snapshot, order, line item, receipt/charge, refund, provider event, reconciliation item |
| Communication | Announcement, consent/suppression, campaign, audience snapshot, outbox job, delivery attempt |
| External/reporting | Sanction application/evidence, software capability evidence, export manifest, submission attempt/acknowledgment |
| Operations | Audit event, upload metadata, incident, import run, backup/restore evidence |

**Required invariants:**

1. A registration, match, job, export, and its referenced children belong to one authorized organization/event. A client cannot supply another tenant's foreign key to bypass scope.
2. An admitted singles entry has exactly one eligible participant; an admitted doubles entry has exactly two distinct eligible participants. The same person cannot occupy both sides of a match.
3. A participant belongs to at most one active entry in a division. A person linked across event registrations remains one conflict resource for scheduling.
4. `admitted_entries + active_holds <= division_capacity`. Capacity reductions below current occupancy are rejected; a separate remediation workflow must resolve occupancy first.
5. Competition dependencies are acyclic; each advancing result resolves at most one winner and one loser destination as specified by its format.
6. At most one authoritative confirmed result revision is current for a match. Confirmation and dependent advancement commit together.
7. Court/person/official time conflicts are validated on commit and again at actual dispatch/start. Authorization alone never makes an invalid start valid.
8. Final standings identify the exact draw, rules, and result revisions from which they were calculated.
9. Historical accepted prices, policies, rulesets, consents, and results are immutable versions. New information creates a new version or superseding record.
10. Audit records contain actor, scope, action, timestamp, correlation ID, referenced revisions, and sanitized change details. Secrets and unnecessary personal text are excluded.
11. UTC instants plus the event's IANA time zone are stored. Ambiguous daylight-saving local times require an offset choice; nonexistent local times are rejected. Server time controls expiry.
12. External IDs are namespaced by provider and owning account/organization. Local IDs are stable opaque identifiers; human-readable codes are scoped aliases.

### 3.22 State machines and transition guards — REQ-STATE

Independent concerns remain separate fields/state machines. A person can be admitted, unpaid, not checked in, and ineligible for a newly changed sanctioned requirement; one overloaded `status` must not hide that combination.

| Concern | States / transitions | Important guard |
| --- | --- | --- |
| Event publication | draft → published → archived; published → cancelled → archived | Publish validation and director permission |
| Registration window | scheduled → open → closed; director may reopen | Reopening does not unlock a draw |
| Competition | setup → ready → live ↔ suspended → completed; cancellation from any unfinished state | Completed requires division finalization or explicit partial/cancelled outcomes |
| Entry admission | incomplete → eligible → admitted or waitlisted; waitlisted → offered → admitted; active states → withdrawn/rejected | Capacity acquired atomically; offered expiry returns to queue policy |
| Capacity hold | active → consumed, expired, or released | One terminal transition; server clock |
| Match | blocked → ready → called → in_progress ↔ suspended → awaiting_confirmation → completed | Dependencies, readiness, resources, and revision checks |
| Match exception | Any permitted pre-completion state → void or administrative result | Reason and director/authorized official decision |
| Result revision | submitted → confirmed or rejected; confirmed → superseded | Supersession requires correction workflow |
| Division certification | provisional → final → reopened → final | All outcomes resolved; no pending incident/submission |
| Online money (R2) | order quoted → payment pending → paid/failed/expired; paid → partial/full refund through separate refund records | Provider evidence and reconciliation, not redirect |
| External reporting (R3) | generated → authorized → queued → sent → acknowledged → accepted/rejected; uncertain → outcome_unknown | Persist evidence at each step; correction can reopen |

Cancelled, archived, and completed are not deletion. Holds, refunds, privacy tasks, and external corrections may still require controlled writes after ordinary event editing is closed.

**Waitlist expiry rule:** an unaccepted expired offer moves the entry to the end of the queue with a visible “offer expired” history and pauses further offers to that entry until it reconfirms interest or a director explicitly re-offers. The next eligible entry is offered the spot. A director can re-offer or remove an entry with a reason. No offer extends beyond registration close; at close, pending offers expire and no new offers are generated until an explicit reopening.

### 3.23 Architecture and interface contracts — REQ-ARCH

Use a modular monolith: one application with a relational transactional database and a background worker, deployable together for small installations. A PostgreSQL-class database is the reference capability level; the exact language, web framework, ORM, authentication library, and hosting target remain implementation-plan decisions.

Modules: identity/access; event setup; registration/admission; competition/rules; scheduling; results; communication; optional finance; external adapters; reporting/audit. Keep draw generation and score/ranking calculations deterministic and separately callable from transport/storage code.

- Public and staff web interfaces call the same validated domain commands; no browser-only enforcement or direct client writes to authoritative records.
- Use server-rendered or equivalently indexable public event pages. Rich desk interaction can enhance a working accessible document structure.
- Start with database-backed durable jobs and an outbox. Dedicated message brokers, search clusters, microservices, and a separate analytics warehouse are not prerequisites.
- Use local or S3-compatible object storage through an interface. The reference deployment must support a non-proprietary storage option.
- Live updates may use server-sent events, WebSockets, or polling. A full-snapshot fallback and explicit stale indicator are mandatory.
- Validate configuration at startup. Missing optional providers disable their actions with a clear explanation; they must not break free casual events.
- R1 development/demo setup must run with synthetic data and a local mail sink, without paid services. Production setup documents TLS, email delivery, backups, secrets, and updates.

**Logical command contract** — endpoint names are illustrative, behavior is normative:

| Command | Input that must be checked | Atomic effect |
| --- | --- | --- |
| `PublishEvent` | Actor, event revision, complete publication fields | Publish revision and enqueue approved notices |
| `AdmitEntry` | Entry members, consent/eligibility, capacity, idempotency key | Acquire spot and return stable admission/queue result |
| `OfferWaitlistSpot` | Queue state, free capacity, unexpired window | Reserve one spot and create one offer |
| `LockDraw` | Eligible roster revision, ruleset, generator inputs | Persist immutable draw and invalidate stale proposal |
| `CommitSchedule` | Expected revision, assignments, all hard constraints | Commit assignments and new schedule revision |
| `StartMatch` | Expected revision, actual player/court/official readiness | Occupy resources and record actual start |
| `ConfirmResult` | Valid outcome, authority, expected match revision | Confirm result, release resources, advance draw, enqueue notices |
| `CorrectResult` | Replacement, reason, impact graph, incident resolution | Supersede atomically and recompute affected state |
| `FinalizeDivision` | All outcomes, no unresolved disputes/corrections | Freeze a final results snapshot |
| `SubmitExternalPackage` | Authorized package hash/revision and connector | Persist submission intent; worker performs external operation |

Every mutation carries a scoped idempotency key where replay can duplicate an operation, plus an expected resource revision when concurrent changes matter. Repeating an identical key/payload returns the original result; reusing it with a different payload is rejected. Validation errors, authorization failures, stale revisions, and provider failures have distinct machine-readable codes and useful human messages.

Idempotency retention must cover the allowed replay window: R1 domain commands retain keys for the event's editable lifetime; provider operation references persist for their financial/reporting record retention. An expired key must not make an already unique payment/result reference repeatable.

### 3.24 Security, reliability, and operations — REQ-OPS

**Security requirements:** enforce tenant authorization on every route and job; use secure session cookies and CSRF protection where applicable; sanitize public rich text; validate input at trust boundaries; use parameterized database access; and keep credentials outside source and exports.

- Auth/recovery links are random, hashed at rest where usable, single-purpose, expiring, and revocable. Consuming a link uses an explicit action rather than a destructive GET vulnerable to email preview scanners.
- Rate-limit sign-in, invitations, registration, uploads, and contact routes. Public-instance event publishing requires a verified organizer contact, with report/hide controls for abusive listings.
- Validate file type/content and size. R1 accepts raster images and CSV where needed; reject active HTML/SVG uploads. R3 evidence PDFs are quarantined/scanned before restricted download and never executed inline as trusted content.
- Proposed limits: 10 MB per image/document; 5 MB/2,000 rows per CSV import; oversized uploads fail before processing. Larger administrative imports need a separate controlled path.
- Export CSV cells defensively against spreadsheet formula execution. Import never executes formulas or fetches referenced URLs.
- Do not fetch arbitrary remote attachment URLs server-side. Any required fetch uses a narrowly scoped adapter with network restrictions.
- Logs use correlation IDs and redact contacts, tokens, private notes, and provider secrets. Operational telemetry defaults to aggregate technical metrics, not third-party behavioral tracking.

**Connectivity and recovery:**

- R1 may cache only previously authorized public/read-only views by default. Private rosters and credentials must not enter general service-worker caches or public CDN responses.
- Losing connectivity disables authoritative writes and shows the last successful sync. Unsent form drafts can remain in page memory with a clear unsaved label; automatic cross-device/offline score replay is excluded.
- Provide a printable recovery pack before play. During an outage, staff record match IDs and results on paper and reconcile through ordinary confirmed entry after reconnection.
- A server-acknowledged write is durably committed to the database before the UI reports success. A lost response can be retried safely with the same operation identity.
- Backups are encrypted and include database and required objects. The reference hosted deployment targets recovery point ≤15 minutes and recovery time ≤4 hours under a documented restore exercise. This does not promise zero loss after a total host disaster; paper records and journals support reconciliation.
- Document deployment-specific backup retention and restore instructions. Restoring to a new installation disables external sends until the operator reviews it, preventing duplicate notices, charges, or result submissions.
- Database migrations preserve revision/audit relationships and have a rollback or forward-recovery plan. Avoid planned schema maintenance during an active event.

**Measurable service targets:** These are acceptance targets to be measured on a documented environment, not claims about an unbuilt system.

| Measure | R1 target and measurement condition |
| --- | --- |
| Public event usability | Key content usable within three seconds on a documented midrange mobile/4G test profile |
| Desk command latency | p95 ≤1 second, excluding external services, with 20 active staff and 100 aggregate domain commands/minute |
| Public board freshness | Confirmed changes visible within five seconds under normal connectivity; stale label after 15 seconds without successful refresh |
| Public read load | 500 simultaneous viewers polling no faster than every five seconds, using public projections/caching |
| Draw/schedule proposal | ≤5 seconds for the supported R1 envelope; infeasible schedules return explanations |
| Print/export | ≤30 seconds for an R1 event; visible job state and safe retry |
| Data integrity | No oversold spots, duplicate confirmed outcomes, or conflicting starts in concurrency fixtures |
| Recovery | A restore exercise meets the stated RPO/RTO with external operations disabled until review |

Track job lag/failure, registration conflicts, result conflicts, stale public projections, failed essential notices, provider unknown outcomes, and backup age. Notify operators about actionable failures with links to recovery steps. Routine passing checks should remain quiet.

## 4. Acceptance Criteria (EARS style)

Every criterion applies to the release shown. Implementation tests must reference these IDs. The examples below supplement all normative requirements in Section 3; passing one happy-path scenario does not replace the underlying invariants.

### 4.1 Access, publication, and registration

- **AC-001 — R1 / REQ-ACCESS:** WHEN a staff member requests an object, export, or live subscription belonging to another organization, the system SHALL deny access without returning that object's private fields or existence details.
- **AC-002 — R1 / REQ-ACCESS:** WHEN a scorer's grant is revoked, the system SHALL reject their next protected read/write and terminate protected subscriptions, even if their browser remains signed in.
- **AC-003 — R1 / REQ-EVENT:** WHEN a director publishes a complete casual event, the system SHALL expose its current permitted details at a stable URL; IF a required field is missing, THEN publication SHALL fail with specific corrective actions and preserve the draft.
- **AC-004 — R1 / REQ-EVENT:** WHEN an event is unlisted or private, the system SHALL omit it from discovery and indexing; IF it is private, THEN unauthenticated URL access SHALL also fail.
- **AC-005 — R1 / REQ-EVENT:** WHEN an event is cloned, the system SHALL produce an unpublished settings copy with no copied participants, acceptance records, results, money records, or approval evidence.
- **AC-006 — R1 / REQ-REG:** WHEN two complete eligible entries request the last available division spot concurrently, the system SHALL admit at most one and return an accurate waitlist/full result to the other.
- **AC-007 — R1 / REQ-REG:** WHEN a doubles captain invites a partner, the system SHALL display incomplete status and consume no capacity; WHEN both adults complete their requirements, the system SHALL attempt admission once for the whole team.
- **AC-008 — R1 / REQ-REG:** IF one person already occupies an active entry in a division, THEN another entry containing that verified person SHALL be rejected without affecting the original entry.
- **AC-009 — R1 / REQ-REG:** WHEN an offer expires or is declined, the system SHALL release exactly one reservation and offer the next eligible entry once; IF registration is closed, THEN it SHALL issue no new offer.
- **AC-010 — R1 / REQ-DIVISION:** WHEN eligibility is evaluated, the system SHALL use the published age reference date, skill boundaries, team aggregation policy, and evidence source; unknown evidence SHALL remain unknown.
- **AC-011 — R1 / REQ-REG:** WHEN a roster import contains invalid rows or duplicate candidates, the system SHALL show a no-write preview; WHEN the director commits selected valid rows, the system SHALL import that selection atomically and report its outcome.
- **AC-012 — R1 / REQ-PRIVACY:** IF an imported, assisted, or self-registered participant is under 18 on the required reference date, THEN R1 SHALL refuse admission rather than bypassing the adult-only limit.
- **AC-013 — R1 / REQ-CHECKIN:** WHEN only one doubles partner has checked in, the system SHALL keep the entry unavailable for a match start and identify the missing partner action to authorized staff.
- **AC-014 — R1 / REQ-CHECKIN:** WHEN a no-show grace period ends, the system SHALL flag a director decision without automatically confirming a forfeit.

### 4.2 Draws, scores, and scheduling

- **AC-015 — R1 / REQ-FORMAT:** WHEN a seven-entry round robin is generated, the system SHALL produce 21 distinct pairings over seven logical rounds, with one rest entry per round and no repeated pair or self-match.
- **AC-016 — R1 / REQ-FORMAT:** WHEN a five-entry elimination draw is generated from seeds 1–5, the system SHALL allocate byes to seeds 1–3 and require four played completions to determine a champion if nobody withdraws.
- **AC-017 — R1 / REQ-FORMAT:** WHEN identical frozen inputs are regenerated, the system SHALL produce the same draw; IF the roster revision has changed before commitment, THEN it SHALL reject the stale proposal.
- **AC-018 — R1 / REQ-SCORE:** WHEN final scores for target 11 are submitted, the system SHALL accept 11–9 and 12–10 and reject 11–10, 12–8, negative, fractional, and tied scores, preserving the draft on error.
- **AC-019 — R1 / REQ-SCORE:** IF a best-of-three match already has a two-game winner, THEN the system SHALL reject any third played game appended after that winning sequence.
- **AC-020 — R1 / REQ-SCORE:** WHEN a retirement or walkover is confirmed, the system SHALL retain actual played scores where present, identify the administrative outcome, and avoid inventing complete games or point totals.
- **AC-021 — R1 / REQ-SCORE:** WHEN round-robin entries tie on wins, the system SHALL apply the published criteria in order and display the deciding criterion; IF the tied group lacks all normal head-to-head completions, THEN that criterion SHALL be skipped for the entire group.
- **AC-022 — R1 / REQ-SCORE:** WHEN two staff confirm different submissions against the same match revision concurrently, the system SHALL commit at most one and return a conflict with the current result to the other.
- **AC-023 — R1 / REQ-SCHEDULE, REQ-VENUE:** IF two proposed matches share a player through different doubles partners or divisions, THEN schedule commitment SHALL reject an overlap or rest-period violation, including an authorized private accommodation constraint without publishing its reason.
- **AC-024 — R1 / REQ-SCHEDULE:** WHEN two staff attempt to reserve or start different matches on one court concurrently, the system SHALL allow only one valid occupancy and explain the conflict to the other.
- **AC-025 — R1 / REQ-SCHEDULE:** IF a previous match runs past its estimate, THEN the next match involving that person/court SHALL remain blocked until actual completion and required rest/resource release.
- **AC-026 — R1 / REQ-SCHEDULE:** WHEN available court time cannot satisfy the configured event, the system SHALL return unscheduled matches and their blockers rather than inventing simultaneous assignments or silently shortening scoring.
- **AC-027 — R1 / REQ-SCHEDULE:** WHEN a director applies a rain hold, the system SHALL prevent new starts in scope, preserve existing scores, and generate a reviewable schedule revision on resumption.
- **AC-028 — R1 / REQ-SCORE:** WHEN a correction changes a winner before descendants have started, the system SHALL supersede the result and update the affected draw, assignments, standings, and notices atomically.
- **AC-029 — R1 / REQ-SCORE:** IF an affected downstream match has started, THEN an ordinary correction SHALL be rejected and the branch frozen for the documented incident/void-and-replay procedure.
- **AC-030 — R1 / REQ-SCORE:** WHEN a confirmed correction changes a finalized division, the system SHALL reopen it visibly, preserve the previous final snapshot, and require a new certification.
- **AC-031 — R1 / REQ-STATE:** IF required matches or correction incidents remain unresolved, THEN the system SHALL refuse normal division finalization and offer an explicitly partial-results report where appropriate.

### 4.3 Marketing, notifications, and privacy

- **AC-032 — R1 / REQ-MARKET:** WHEN an organizer generates a flyer or invitation, the system SHALL use the current published event details, include a usable text URL alongside the QR code, and require no external social account.
- **AC-033 — R1 / REQ-MARKET:** WHEN an event's venue/date changes, the system SHALL update its public page and identify previously generated assets as belonging to an older revision.
- **AC-034 — R1 / REQ-NOTIFY:** WHEN the notification worker retries a committed event update, the system SHALL reuse its delivery identity; provider acceptance SHALL not be displayed as confirmed human receipt.
- **AC-035 — R1 / REQ-NOTIFY:** IF email delivery fails, THEN the registration or score transaction SHALL remain committed, the event board SHALL remain accurate, and staff SHALL see the delivery failure with a retry/recovery action.
- **AC-036 — R1 / REQ-PRIVACY:** WHEN a visitor views pages, JSON, live events, images, or exports, the system SHALL disclose no participant contacts, birth dates, private accommodations, payment references, or restricted documents.
- **AC-037 — R1 / REQ-PRIVACY:** WHEN the configured retention deadline passes without a documented hold, the system SHALL delete or deidentify the covered private data and invalidate its controlled derived exports/caches.
- **AC-038 — R2 / REQ-MARKET:** WHEN an organizer prepares a promotional campaign, the system SHALL exclude unconsented/suppressed recipients, show the eligible audience count, and wait for a send confirmation.
- **AC-039 — R2 / REQ-PRIVACY:** WHEN a guardian registers a junior, the system SHALL require the guardian workflow, route communications appropriately, and apply limited public identity defaults.

### 4.4 Money, providers, and sanctioning

- **AC-040 — R1 / REQ-MONEY:** WHEN staff record an external payment, the system SHALL label it as staff-recorded, preserve the receipt reference and actor, and never imply processor verification.
- **AC-041 — R2 / REQ-MONEY:** WHEN duplicate or out-of-order payment webhooks arrive, the system SHALL authenticate them, record each provider event once, and preserve the correct current money/admission state.
- **AC-042 — R2 / REQ-MONEY:** IF payment succeeds after reservation expiry and capacity has been filled, THEN the system SHALL record paid-without-admission and route reconciliation/refund without exceeding capacity.
- **AC-043 — R2 / REQ-MONEY:** WHEN the same refund request is repeated after a timeout, the system SHALL reconcile the existing provider operation before any retry and SHALL never refund more than the unrefunded captured amount.
- **AC-044 — R2 / REQ-INTEGRATION:** IF provider access is missing or a capability is unsupported, THEN the system SHALL disable the affected external action while allowing supported casual event operations.
- **AC-045 — R3 / REQ-SANCTION:** IF software eligibility, an applicable supported profile, or required event approval evidence is missing, THEN the system SHALL block an approved-sanctioned-operation claim and list the unmet gates.
- **AC-046 — R3 / REQ-SANCTION:** WHEN a director uploads approval evidence without independent verification, the system SHALL display recorded evidence with its method and SHALL not label it independently verified.
- **AC-047 — R3 / REQ-SANCTION:** IF a selected sanctioned configuration requires a rule/format not implemented by its profile, THEN the system SHALL refuse the configuration and SHALL not substitute a casual rule.
- **AC-048 — R3 / REQ-SANCTION:** WHEN an eligibility source times out, approval expires, or a profile passes its review date, the system SHALL expose the corresponding unknown/expired/review-required state and block the operations governed by it.
- **AC-049 — R3 / REQ-SANCTION:** WHEN a report is exported or transmitted, the system SHALL retain its revision/hash and actual delivery evidence; acceptance SHALL require the receiving body's evidence.
- **AC-050 — R3 / REQ-INTEGRATION:** WHEN a previously submitted result is corrected locally, the system SHALL mark the external record correction-required until a supported correction is acknowledged or reconciled.

### 4.5 Accessibility, recovery, and architecture

- **AC-051 — R1 / REQ-UX:** WHEN a user runs creation, registration, check-in, court assignment, score entry, and results viewing using keyboard controls, the system SHALL provide all required actions without dragging, hovering, scanning, or pointer precision.
- **AC-052 — R1 / REQ-UX:** WHEN primary desk controls are exercised through voice control, their visible labels SHALL correspond to accessible names and repeated row controls SHALL identify the relevant player/match.
- **AC-053 — R1 / REQ-UX:** WHEN the interface is tested at a 320 CSS-pixel viewport and with zoom/reduced motion/screen-reader operation, the core workflows SHALL remain usable and bracket information SHALL have an equivalent list representation.
- **AC-054 — R1 / REQ-OPS:** WHEN connectivity is lost, the system SHALL identify stale data and unsaved drafts, prevent authoritative writes from appearing successful, and support paper-based reconciliation after reconnecting.
- **AC-055 — R1 / REQ-ARCH:** WHEN the server commits a result but its response is lost, retrying the same command SHALL return the committed outcome without duplicate advancement, audit mutation, or notice intent.
- **AC-056 — R1 / REQ-DATA:** WHEN a schedule uses an ambiguous/nonexistent daylight-saving local time, the system SHALL require a valid explicit instant instead of silently shifting it.
- **AC-057 — R1 / REQ-REPORT:** WHEN a full authorized archive is restored into a clean compatible instance, the system SHALL reproduce competition/results relationships, report remapped ownership, and keep all external side effects disabled until reviewed.
- **AC-058 — R1 / REQ-OPS:** WHEN malicious rich text, spreadsheet-formula cells, forged foreign keys, or oversized files enter an input boundary, the system SHALL reject/sanitize safely and prevent script execution, tenant leakage, and partial authoritative writes.
- **AC-059 — R1 / REQ-OPS:** WHEN the documented R1 workload is exercised, the system SHALL meet the latency/freshness targets or record the measured failure and narrower supported operating envelope before release.
- **AC-060 — R1 / REQ-OPS:** WHEN a backup is restored under the recovery exercise, the installation SHALL recover within its documented RPO/RTO, report what could have been lost, and require review before resuming external operations.
- **AC-061 — R2 / REQ-FORMAT:** WHEN unequal pools qualify teams, the system SHALL apply the published finish-place/pool-order mapping and SHALL not rank cross-pool teams by unadjusted point totals.
- **AC-062 — R2 / REQ-FORMAT:** WHEN the undefeated finalist loses the first championship match under the true double-elimination preset, the system SHALL create the reset final; a bye SHALL not count as a loss.
- **AC-063 — R2 / REQ-SCORE:** WHEN a player submits a score and the opponent disputes it or does not respond, the system SHALL preserve an unresolved submission until the selected confirmation policy is satisfied.
- **AC-064 — R1 / REQ-JOURNEY:** WHEN a director completes the 32-player pilot scenario in Section 5, the system SHALL retain a complete event record and publish only the permitted final results without a parallel working spreadsheet.

## 5. Verification and release gates

### 5.1 Verification approach

During implementation, run targeted checks for the behavior changed: pure-function tests for draw/scoring/ranking logic, database concurrency tests for capacity and result commitment, permission tests across tenants, and focused browser journeys for operator/player interactions. Do not repeatedly run a full suite or repository analysis for small changes. At the final integration gate, provide Ryan the command for any lengthy full suite or load/restore exercise he is to run.

Use synthetic names and contact addresses in fixtures. Provider sandbox evidence, mocked responses, real-provider acceptance, automated accessibility findings, and observed assistive-technology use must be labeled separately. Implementation evidence is recorded in IMPLEMENTATION.md. Only its explicitly listed checks have run; unverified criteria remain open.

Required deterministic fixture families:

- Round robins for 2–16 entries, including odd counts, pair uniqueness, rest rounds, and formula match counts.
- Elimination draws for 2–16 entries, byes, deterministic seeds, withdrawals, and corrections before/after descendants start.
- Normal/invalid/deuce scores and every administrative outcome; best-of-three terminal-game boundaries.
- Two-way/three-way/all-entry ties, missing head-to-head results, and stable tie explanations.
- Competing admissions, holds, expiry, withdrawals, duplicate imports, and retries against real database transactions.
- Shared players across divisions; pinned schedules, actual overruns, rest, blocked courts, and impossible schedules.
- Role removal, forged cross-tenant IDs, public serializers, protected subscriptions, expired links, and CSV injection.
- Lost responses, duplicated/out-of-order jobs, reconnect revision gaps, archive/restore, and daylight-saving edges.
- R2/R3-specific fixtures for payment ambiguity, guardians, double elimination, profile constraints, external correction, and report provenance.

### 5.2 End-to-end pilot scenarios

| Scenario | Setup and required evidence |
| --- | --- |
| R1 community event | 32 adults, 16 doubles teams, four courts, four divisions of four teams each, one round robin per division: 24 matches total. Publish, share, register, check in, run, certify, and export. Include one waitlist offer and one pre-draw partner replacement. |
| R1 exception rehearsal | Separate synthetic five-team elimination event with a bye, a no-show, a duplicate score submission, a correction before advancement starts, and an attempted correction after a descendant starts. Record incident resolution and revised results. |
| R1 disruption rehearsal | Two staff devices contend for a court, one shared player appears in two divisions, a rain hold shifts the schedule, email fails, connectivity drops, and paper scores are reconciled after reconnecting. |
| R1 privacy/accessibility review | Complete the critical workflows with keyboard, screen reader, and voice-control checks on the selected browser/device matrix. Inspect public responses for private data and verify protected fields with representative roles. |
| R2 operational rehearsal | Run pools into playoffs and a double-elimination reset fixture; exercise a guardian registration, expired paid reservation, partial refund, unsubscribed campaign recipient, and provider outage. |
| R3 supported sanctioned pilot | Use a real permitted workflow for the selected body/profile and record software eligibility, event approval, eligibility evidence, required officiating, finalized package, and receiving-body acknowledgment/acceptance. Test fixtures cannot substitute for this evidence. |

The browser/device matrix for R1 SHALL include current stable desktop Chrome/Firefox/Safari and mobile Safari/Chrome at the time of release, with versions recorded in evidence. At least one screen-reader desktop/browser pairing, one mobile screen reader, and a voice-control workflow must be observed; automated scans supplement these checks.

### 5.3 Release gates

**R1 gate:** All R1 criteria pass within the declared envelope; the community and disruption rehearsals complete; no known blocker remains in admission, authorization, score advancement, recovery, or primary accessible workflows. Setup, event-day recovery, backup/restore, export/import, and limitations are documented. The owner has resolved the distribution/license decision before any open-source release claim.

**R2 gate:** R1 remains functional; each enabled R2 feature meets its criteria; junior/privacy and payment operating policies are defined; provider capabilities and costs are explicit; the larger envelope is measured before larger events are accepted. Unsupported optional features remain disabled.

**R3 gate:** At least one body/profile has a versioned requirements mapping with exact source clauses, allowed combinations, test fixtures, external software eligibility evidence where required, and a completed permitted pilot/reporting path. Marketing accurately names the supported subset. A body or provider dependency can delay R3 without making a complete R1/R2 casual release unusable.

**Definition of done for an implementation slice:** intended behavior is reflected in this spec; relevant acceptance IDs have evidence; errors/recovery and accessibility are included; changed data migrations and authorization boundaries are reviewed; known limitations are visible; and no unverified provider or compliance claim is introduced.

## 6. Out of Scope

The following are excluded from R1–R3 unless a later specification explicitly adds them:

- Becoming a sanctioning body, issuing memberships, manufacturing official ratings, or independently awarding external qualification points.
- Guaranteeing event insurance, legal enforceability of waivers, participant medical suitability, or real-world venue safety.
- A professional tour management system, betting, prediction markets, automated prize disbursement, or player contracts.
- Native iOS/Android applications, wearable scoring hardware, camera-based line calls, or electronic referee replacement.
- Peer-to-peer offline synchronization, multi-device offline score merging, or automatic replay of offline financial actions.
- A general social network, unrestricted participant messaging, scraped contact lists, paid advertising management, or autonomous promotional outreach.
- Court reservation inventory sold to the public, facility access control, equipment rental, retail merchandise, and accounting/tax filing.
- Rotating-partner/Americano sessions, Swiss, ladders, season-long leagues, and specialized team formats without separate format specifications.
- Automatic international sanctioning coverage, universal rating equivalence, or multilingual support before dedicated policies and localization work.
- Federation between independently hosted instances. Data portability does not imply shared identity, cross-instance search, or synchronized results.
- Subscription billing, licensing tiers, platform commissions, enterprise SSO, or other commercialization assumptions.
- Importing a rulebook wholesale, distributing protected logos without permission, or treating scraped source text as an executable policy.
- The original specification-only request excluded framework selection and implementation. The later local implementation authorization supersedes that request boundary; it does not remove any product requirement or external release gate.

## 7. Decisions and uncertainties to carry into planning

The draft is complete enough to review and scope development, but it is not a locked implementation contract until the owner accepts the assumptions. Resolve decisions only when they become material; do not turn this register into a questionnaire for Ryan.

| ID | Decision or uncertainty | Current position | Effect |
| --- | --- | --- | --- |
| D-01 | Meaning of “open” | Proposed open-source/self-hostable; user clarification pending | Determines distribution constraints, not the core event workflow |
| D-02 | License | No license selected | Must be decided before distribution claims; no license file created here |
| D-03 | Implementation stack | Django 5.2 LTS, Python 3.13, SQLite immediate transactions; PostgreSQL configuration available | Local runtime implemented; PostgreSQL verification remains open |
| D-04 | Hosting scope | Both single-organization self-hosting and a shared instance are modeled | Choose the first deployment and maintenance budget during planning |
| D-05 | First release size | Proposed R1 limits and 32-player pilot | Increase only with corresponding verification |
| D-06 | Payment provider and recipient | Not selected; R1 supports free/external collection | Does not block R1; blocks online collection |
| D-07 | Governing body/software acceptance | USA Pickleball is the initial candidate; no approval established | Blocks an R3 support claim, not casual operation |
| D-08 | Current rule/profile details | Sources identified; clause-level mapping not yet produced | Required work for the first sanctioned profile |
| D-09 | Ratings integration | No credentials, partnership, terms, or schemas validated | Use local history/generic exports until adapter prerequisites are satisfied |
| D-10 | Junior and sensitive-data policies | Adult-only R1; guardian/retention contracts specified for later | Must be completed before enabling the affected features |
| D-11 | Pilot venue/operator | No real event committed | Synthetic rehearsal first; arrange a real pilot separately |

Progress is in roadmap.md and acceptance evidence in IMPLEMENTATION.md. R2/R3 influence stable data boundaries; incomplete or externally dependent capabilities must not be represented as delivered.

## 8. Sources and verification limits

Research checked October 3, 2026, using the America/Chicago user date. These links support the external facts identified above; the proposed application behavior is an original product specification. Recheck sources when implementing an adapter or activating an event profile.

| Source | What it informed | Limit |
| --- | --- | --- |
| [USA Pickleball sanctioning](https://usapickleball.org/sanctioning/) | Approval categories, eligibility, and software-provider dependency | No determination that this unbuilt platform is approved |
| [USA Pickleball rulebook index](https://usapickleball.org/rules/) | Need to select and pin a current rule edition | The complete 2026 rulebook has not been mapped into executable requirements here |
| [USA Pickleball formats guidance](https://usapickleball.org/sanctioning/formats/) | Separate supported competition combinations and reconcile dated guidance | Contains 2025-specific language; do not treat the whole page as a definitive current profile |
| [USA Pickleball event operator guide](https://usapickleball.org/sanctioning/event-operator-guide/) | Operational workflow and external reporting as separate responsibilities | Application/checklist/reporting deadlines must be reverified for the chosen event/profile |
| [DUPR club resources](https://www.dupr.com/club-resources) | Integration partner and manual-upload paths | No API contract, integration permission, or CSV compatibility verified for this project |
| [W3C WCAG 2.2](https://www.w3.org/TR/WCAG22/) | Accessibility evaluation target | A design target is not a conformance finding |

During specification drafting, no organization was contacted, no account/provider was connected, no event was published, and no application behavior was verified. The later October 4 local implementation and synthetic verification are documented separately; no external publication or provider connection occurred.

# Open Pickleball Tourney

## Active direction: browser edition (October 5)

Ryan selected one organizer using one computer/tablet. The active UI is the
Hugo static site in `site/`; start its development preview with `./play`.
Read `site/README.md` and the October 5 contract at the top of `spec.md`.
The Django application is archived in `django-edition/` (see below).

- Browser code: `site/assets/js/engine.mjs` (pure rules and backup validation),
  `competition.mjs` (brackets, pools and social rotations),
  `desk.mjs` (time planner, shareable results text, display-board model),
  `storage.mjs` (locked browser saving), `app.js` (guided UI).
- Hugo: `site/layouts/home.html`, `home.serviceworker.js`, `site/hugo.toml`;
  readable CSS in `site/assets/css/style.css`. No npm install or external assets.
- Build: `hugo --source site --cacheDir "$PWD/site/.cache" --cleanDestinationDir --panicOnWarning`.
- Targeted browser checks only: `node --test site/tests/browser-rules.test.mjs site/tests/formats.test.mjs site/tests/desk.test.mjs`.
  Do not run the unrelated Django suite for static-only edits.
- Records belong to one browser/address; never claim shared editing or server
  backup. Saving failures must keep recoverable data and visibly report failure.
- Seven casual formats: round robin, round robin/playoffs, pools/playoffs,
  single elimination, double elimination, rotating partners and king/queen.
  Fixed formats: 2–16 entries, 1–8 courts. Social: 4–16 individuals; ladder
  needs exactly four per court. One game to 11/15/21, win by two.
- Preserve version 1 round-robin backups and the existing storage key. New
  formats write version 2 with score-to-opponent bindings and confirmed
  qualification records. All corrections use `reviseTournament` for a
  reviewable consequence preview. No sanctioned-event claims.
- Static output is `site/public/` (ignored). `.github/workflows/pages.yml` is
  prepared to publish `site/` as the GitHub Pages micro site (the `docs/`
  showcase is archived and not what it serves). It has never run: enabling Pages,
  pushing and triggering it are Ryan's actions, not an agent's.

## Product scope (October 18)

Impromptu tournaments among friends and small clubs, never major or sanctioned events. Organizer on a phone at the courts, calling games aloud; typical group 4–8, up to 16 supported; all seven formats stay visible, with the picker suggesting one from who is playing, headcount and time. Top quality bar: fair, balanced play. It should be a joy to use.

## Archived Django edition (`django-edition/`, archived October 18; do not extend)

Ryan archived this edition. Only touch it if he asks. Local Django 5.2 / Python 3.13 app for adult community pickleball events. Its README, IMPLEMENTATION, roadmap, spec and OPERATIONS docs live in `django-edition/`; the root docs cover the browser edition only. Its CI definition is parked at `django-edition/ci/test.yml` (not in `.github/workflows/`).

- Run from `django-edition/`: `./tour` (isolated demo) or `./tour serve`. Python is `.venv/bin/python` (moved with it; its console-script shebangs may need `uv pip sync requirements.txt` to refresh).
- Tests: `.venv/bin/python manage.py test` is the whole suite (about 5 s). **Give Ryan this command and let him run it; do not run suites in a session.**
- Layout: `engine.py` pure tournament logic; `services.py`/`operations.py` mutations via `@command` (event row lock, revision check, idempotency key, audit); `views.py`/`desk_views.py` thin HTTP; `portability.py` archives/CSV; `delivery.py` mail worker and maintenance.
- Mutations go through `@command`; never write event state directly from a view. Unvalidated model constraints that involve `event` need explicit form checks (ModelForm skips them).
- Boundaries: no `git add`/`commit`/`push`, deploy or publish unless Ryan names the action. GitHub Pages enablement and the license are his decisions. Keep docs honest: never mark R1/R2/R3 complete, claim provider approval, or call untested behavior verified.

@AGENTS.md

## Source change checks

Trace affected imports, callers, routes, templates, and focused tests with native repository searches and source reads before editing. Keep unresolved references explicit and follow Ryan's current verification instructions. Staging, commits, pushes, deployment, and publication require his explicit delegation of that action.

# Open Pickleball Tourney

A local Django application for adult community pickleball: registration, check-in, draws, court scheduling, scores, results, and portable event records. Implementation is in progress. **The local demo runs; the R1 release gate is not complete.** See [IMPLEMENTATION.md](IMPLEMENTATION.md) for evidence and limits, [roadmap.md](roadmap.md) for the next work, and the static documentation showcase in [`docs/`](docs/) (not yet published; see the last section).

## Start the local demo

From this directory:

```sh
./tour
```

Open [127.0.0.1:8000](http://127.0.0.1:8000/) and choose **Open organizer demo**. No password or external account is needed. The launcher migrates the isolated demo database, seeds missing demo records, starts a local mail worker, and serves only on loopback. Ctrl-C stops the server and worker. Re-running preserves your current demo work.

- **The Saturday Social:** 32 synthetic adults, 16 doubles teams, four divisions, four courts, and 24 round-robin matches. Start with Players & check-in, then Courts & schedule and Matches & scores.
- **Next Week's Rally:** an empty upcoming event for practicing registration, individual partner acceptance, imports, and draws.
- **Local mailbox:** shows synthetic queued notices and secure links without transmitting email. The demo always uses file mail and `.data/demo`; normal data stays separate.
- Demo dates are set when seeded. The command never resets them behind your back. Clone settings into a new dated event to practice again after the initial demo date passes.

The existing `.venv` is installed. On a fresh checkout with Python 3.13 and `uv` available:

```sh
uv venv --python 3.13
uv pip sync requirements.txt
./tour
```

## Your own local events

```sh
./tour serve
```

This uses `.data` by default, leaves demo access off, and starts a worker alongside the loopback server. In another terminal, generate your initial private sign-in link:

```sh
.venv/bin/python manage.py organizer_link you@example.org
```

Replace the address once with yours, open the printed 15-minute link, and choose Continue. Keep that link private. Create an event, review its policies/divisions, and publish **within your local installation** when ready. Serving this app locally does not publish it to the internet.

Normal email defaults to `.data/mail` files. Public email-link registration on a hosted instance needs a configured delivery backend and worker. Environment variables are documented in [.env.example](.env.example); the app does not automatically load `.env`. The served (`gunicorn`) entrypoint defaults to `DEBUG=0` and closed organizer sign-up; local `manage.py` and `./tour` keep debug-friendly defaults.

## Event-day workflow

1. Create an event or clone reusable settings. Clones are private drafts without participants, results, payments or approval evidence.
2. Configure adult divisions, capacity, scoring, venue hours and event policies. Share the published page or printable flyer.
3. Register participants through individual email links, assist them at the desk, or preview/import a CSV. Doubles partners accept separately; incomplete teams hold no place. CSV import sends invitations only when explicitly selected.
4. Record private accommodations and check in every active partner. Generate a draw preview and commit it after reviewing entries.
5. Preview and commit court assignments or manually set/pin a ready match's time. Calls and starts recheck actual court occupancy, player conflicts and rest. A blocked court suspends play and prevents resumption until reopened.
6. Enter completed game totals, review the named sides and winner, and confirm. Retirement can retain a separate incomplete game. Corrections preserve superseded results and reject changes that would silently alter started dependent matches.
7. Certify completed divisions, or explicitly label interrupted competition as partial. Export public standings, a roster without contacts, a private archive, or a generic result package.

A scorer must have an active event scorer role **and** an assignment to the match. Revoking the grant blocks their next protected request. Director and desk capabilities are distinct from promotion and finance access.

## Useful commands

```sh
# Lightweight configuration/model check
.venv/bin/python manage.py check

# One bounded worker pass using the configured email backend
.venv/bin/python manage.py work_outbox --once

# Whole suite (engine + runtime; it is the only discovery target and runs in seconds)
.venv/bin/python manage.py test
```

Real concurrent PostgreSQL clients, provider delivery, load testing, browser/device coverage and assistive-technology checks remain separate work. CI (`.github/workflows/test.yml`) runs the checks and suite on every push and pull request.

## Documentation & online showcase

A static documentation portal lives in [`docs/`](docs/) with a deploy workflow at [`.github/workflows/pages.yml`](.github/workflows/pages.yml). **It is not published yet:** GitHub Pages must first be enabled for the repository (Settings → Pages → Source: GitHub Actions); until then the workflow fails. Pages hosts only static documentation; the tournament application itself runs locally.

See [OPERATIONS.md](OPERATIONS.md) for backups, restores, uncertain delivery, and hosting boundaries. No license has been selected; this project does not yet claim an open-source release or sanctioned-event approval.

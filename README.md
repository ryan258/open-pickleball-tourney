# Open Pickleball Tourney

**The new direction is a simple browser tournament desk for one organizer on one
computer or tablet.** The Hugo site in [`site/`](site/) handles event setup,
fixed singles/doubles entries, a round-robin schedule, reviewed scores, standings,
printing, browser-local saving, and downloadable backup/restore. There are no
accounts or remote data services. It supports 2–16 entries on 1–8 courts.

For a local development preview:

```sh
./play
```

Open [localhost:1313](http://localhost:1313/). **Try a practice tournament** is a
ready-to-play example; **Start a tournament** begins your own event. `./play`
is a maintainer command using the installed Hugo. Once the site is hosted,
organizers will only need its address and a browser. The intended home is a
GitHub Pages micro site, updated by pushing changes to `main` (see
`.github/workflows/pages.yml`), with a downloadable offline copy for organizers
who prefer a double-click or a screen/board computer. **This work is local; Pages is not enabled and
the browser edition has not been published.**

Tournament records stay in the same browser and website address. Download a copy
before clearing browser data, changing addresses/devices, or starting a new
event. Browser backups are separate from Django archives. A production static
build can reopen offline after its footer confirms that caching succeeded;
the Hugo development preview does not install the offline worker.

See [`site/README.md`](site/README.md) for the bounded workflow, local build,
targeted checks, and recovery behavior. [IMPLEMENTATION.md](IMPLEMENTATION.md)
records evidence and limits; [roadmap.md](roadmap.md) records the active direction.

## Existing Django edition

The earlier local Django application remains available for its broader adult
community-event workflow: registration, check-in, draws, scheduling, scores,
and portable event records. Its R1/R2/R3 release gates remain incomplete.
The instructions below apply to that edition. The `docs/` showcase still
describes that earlier edition; the Pages workflow now serves the browser
edition instead, so `docs/` is not published anywhere.

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

A static documentation portal for the Django edition lives in [`docs/`](docs/). It is **not published and has no deploy workflow**: a repository serves one Pages site, and [`.github/workflows/pages.yml`](.github/workflows/pages.yml) is now prepared to publish the browser edition from `site/` (after Pages is enabled under Settings → Pages → Source: GitHub Actions). The Django application itself runs locally.

See [OPERATIONS.md](OPERATIONS.md) for backups, restores, uncertain delivery, and hosting boundaries. No license has been selected; this project does not yet claim an open-source release or sanctioned-event approval.

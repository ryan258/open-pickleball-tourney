# Operations and recovery

## Runtime

`./tour` starts the isolated synthetic demo; `./tour serve` starts the normal local installation. Both run a managed worker and Django's development server on `127.0.0.1:8000`. Stop with Ctrl-C. Neither is a production deployment command.

Outside the launcher, the application and worker are separate processes:

```sh
.venv/bin/python manage.py migrate --noinput
.venv/bin/python manage.py collectstatic --noinput
.venv/bin/python manage.py runserver 127.0.0.1:8000
# Separate terminal with the same environment:
.venv/bin/python manage.py work_outbox
```

A future hosted installation should run a supervised WSGI process (gunicorn is pinned) and worker, with TLS, explicit host/secret settings, protected persistent storage, a reviewed mail backend and tested backups. `DEBUG=0` requires `SECRET_KEY` and enables secure cookies, HTTPS redirects and HSTS. HTTPS reverse-proxy trust and PostgreSQL TLS settings require deployment-specific review; no deployment has been verified. Run `manage.py check --deploy` under the actual production environment before exposing it. The application does not create accounts with password authentication by default.

## Notification evidence

Registration and results commit independently of delivery. The worker uses durable claims and a stable `Message-ID` for each message. File mail is **saved local**; a transport's positive return is **accepted**, never proof that a person received or read it.

A crashed send or transport exception becomes **uncertain**. These rows are not automatically retried. In **Activity & delivery**, reconcile the displayed Message-ID against mail/provider evidence, then record acceptance, suppress a resend, or explicitly attest non-acceptance and queue a retry. At most three attempts are allowed. The stable identity is retained on retry; provider-side deduplication is not guaranteed.

Marketing messages are suppressed because no campaign/opt-in workflow is enabled. Restored events suppress outbound messages. The worker expires waitlist offers, requeues eligible next entries, clears old rate buckets and removes auth tokens seven days after expiry. Participant-data retention/deidentification is **not implemented**; do not treat token cleanup as a privacy-retention workflow.

## During a connectivity problem

Print **Courts & schedule → Print recovery pack** before the event. The pack carries the event revision and match codes. Write actual start/end times, scores, outcomes and who recorded each result. After reconnecting, review current server state before entering and confirming each paper result. Never assume a lost response means a write failed; matching operation keys replay committed results safely.

The browser displays offline/stale status and never automatically reloads active forms. The live board checks event revisions every ten seconds while visible and unpaused and offers an explicit refresh. It does not merge updates into an active form. Form values remain only in the open tab: **automatic draft recovery and offline authoritative writes are not implemented**. A failed request may require reviewing and resubmitting the page.

## SQLite backup and restore

Normal local data:

```sh
.venv/bin/python manage.py backup_local --output .data/backups/event-day.tar.gz
.venv/bin/python manage.py restore_local .data/backups/event-day.tar.gz --output-dir .data/restored-event-day
```

Demo data:

```sh
TOURNEY_DATA_DIR="$PWD/.data/demo" .venv/bin/python manage.py backup_local --output .data/backups/demo.tar.gz
```

Choose new output names each time. Existing files/directories are never overwritten. Backups contain a consistent SQLite snapshot and SHA-256 manifest, created with owner-only file permissions. They contain private participant and account data. Store them as private backups. They exclude file mail, process environment, and external provider credentials.

Restoration verifies the manifest and SQLite integrity, writes into a new directory, invalidates sign-in tokens and sessions, disables event outbound messages, and marks queued/in-flight deliveries uncertain. The previous installation remains untouched. Review the snapshot timestamp in `RESTORE-REVIEW.json`; changes after that instant are not present. Use a fresh trusted operator link after restoration. Review messages before re-enabling any external actions; this release intentionally has no one-click restore-and-resend control.

To inspect a restored copy with its own local server, stop any other server on port 8000 and use:

```sh
TOURNEY_DATA_DIR="$PWD/.data/restored-event-day" ./tour serve
# Another terminal, same directory selection:
TOURNEY_DATA_DIR="$PWD/.data/restored-event-day" .venv/bin/python manage.py organizer_link you@example.org
```

A separate-directory SQLite backup/restore completed successfully on October 4 with synthetic data. Its integrity and recovery suppression were checked. This was not a timed disaster exercise, an off-machine recovery, or a measured RPO/RTO. Choose backup frequency and off-machine storage before real use. PostgreSQL installations must use native database backups; the local backup commands refuse PostgreSQL.

## Event archives

The full event archive is distinct from an installation backup. It includes configuration, participants, membership/acceptance fields, entries, draw inputs, historical matches/results, manual receipts, packages and audit records. It excludes user accounts, staff grants, login tokens, operation keys and mail bodies. Export fields are allowlisted. Authenticated directors can import a validated archive into their organization as a new private draft; IDs are remapped, original archive provenance is recorded, approval becomes review-required, and outbound messages stay disabled.

Hashes detect corruption; they do not authenticate a sender or independently verify event claims. Preserve the source archive for original actor attribution and pre-remapping package hashes. Restored historical actors are not linked to local accounts. No external acceptance is reasserted by an import. The tested round trip used a fresh event in a disposable test database; clean-install, cross-version and PostgreSQL archive drills remain open.

## Remaining operational limits

- Scheduling proposes resolved ready matches. Unresolved future bracket rounds are not forecast; resuming a hold requires requesting a new proposal.
- No retention-policy execution, organizational ownership transfer, server draft autosave, or bulk account recovery UI.
- Pool result correction after playoff qualification is blocked. A reviewed workflow to recompute qualification is still needed.
- Large-event load, real simultaneous clients, and crash/failover evidence remain unmeasured.
- No online checkout, SMS, ratings submission or sanctioned-operation adapter is connected. Manual ledger and approval notes do not imply provider verification.

# Implementation plan

The October 3 follow-up authorizes local implementation in one continuous pass. No commit, deployment, publication, or provider enrollment is authorized.

1. Build a Django modular monolith with SQLite immediate transactions for the local installation and PostgreSQL configuration for shared hosting.
2. Implement scoped authentication and event roles, event setup/publication, guest registration, individual doubles consent, waitlists, assisted registration, and check-in.
3. Implement deterministic draws, game validation, standings, corrections, schedule proposals, resource checks, event holds, and certification.
4. Deliver responsive public, player, organizer, desk, promotion, finance, and reporting screens with keyboard/touch controls and plain-language errors.
5. Implement durable outbox delivery, manual financial records, approval evidence, report packages, CSV/JSON portability, and recovery commands.
6. Add focused invariant/concurrency/security/browser verification and document implemented scope honestly. External approval and provider-specific live operations remain gated.

Framework choice: Django 5.2 LTS, Python 3.13+, server templates, vanilla JavaScript, PostgreSQL-compatible models. Installed versions are pinned in requirements.txt. No frontend compilation or paid provider is needed for local use.

The original specification remains the target contract. IMPLEMENTATION.md records delivered behavior, remaining gaps, and evidence; it must not claim release-gate completion from implementation alone.


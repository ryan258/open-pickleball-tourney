# Documentation, Rules & Architecture Showcase

This directory contains the rules reference guide, user guides, and architecture showcase for the project.

## Status

- **Active tournament desk:** the standalone browser edition in [`site/`](../site/) is the primary tournament tool for single-organizer events (7 casual formats, local storage, PWA offline caching). Its intended address is `https://ryan258.github.io/open-pickleball-tourney/` via [`.github/workflows/pages.yml`](../.github/workflows/pages.yml).
- **Django edition:** paused; this `docs/` showcase describes its multi-division architecture and operations for local running (`./tour`). This showcase is not published to GitHub Pages.

## Directory Structure

- [`101-really-good-pickleball-rules-questions-w-answers.md`](101-really-good-pickleball-rules-questions-w-answers.md): Comprehensive 101 rules questions and answers reference, cross-referenced rule-by-rule with the 2026 USA Pickleball Official Rulebook, including explicit comparisons to this app's casual house rules.
- [`index.html`](index.html): Responsive landing page, feature showcase, rules reference links, and tournament operations overview.
- [`style.css`](style.css): Custom dark-athletic design system with responsive card layouts and glassmorphism.
- [`app.js`](app.js): Vanilla JavaScript for interactive quickstart command switching and clipboard copying.
- [`assets/`](assets/): High-resolution visual assets including hero banner graphic.
- [`.nojekyll`](.nojekyll): Prevents Jekyll static site processing on GitHub Pages.

## Architecture & Hosting Boundary

The Django edition of Open Pickleball Tourney is a full-stack Python 3.13 / Django 5.2 LTS web application requiring a dynamic runtime (WSGI/Gunicorn, SQLite/PostgreSQL, background mail outbox worker). 

GitHub Pages is prepared to host the standalone browser edition (from `site/`), not this `docs/` showcase. Live tournament operations for the Django edition are run either locally via `./tour` / `./tour serve` or hosted on an application platform (e.g. Render, Fly.io, Railway, or VPS).

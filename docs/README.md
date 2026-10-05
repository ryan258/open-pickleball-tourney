# Documentation & GitHub Pages Portal

This directory contains the static documentation site, user guides, and architecture showcase published via **GitHub Pages**.

## Live Documentation Site

- **URL**: `https://ryan258.github.io/open-pickleball-tourney/`
- **Source**: `docs/` on `main` branch (deployed via [`.github/workflows/pages.yml`](../.github/workflows/pages.yml); GitHub Pages must be enabled in repository settings first).

## Directory Structure

- [`index.html`](index.html): Responsive landing page, feature showcase, and tournament operations overview.
- [`style.css`](style.css): Custom dark-athletic design system with responsive card layouts and glassmorphism.
- [`app.js`](app.js): Vanilla JavaScript for interactive quickstart command switching and clipboard copying.
- [`assets/`](assets/): High-resolution visual assets including hero banner graphic.
- [`.nojekyll`](.nojekyll): Prevents Jekyll static site processing on GitHub Pages.

## Architecture & Hosting Boundary

Open Pickleball Tourney is a full-stack Python 3.13 / Django 5.2 LTS web application requiring a dynamic runtime (WSGI/Gunicorn, SQLite/PostgreSQL, background mail outbox worker). 

GitHub Pages hosts the public-facing documentation, quickstart guides, and deployment instructions statically, while live tournament operations are run either locally via `./tour` / `./tour serve` or hosted on an application platform (e.g. Render, Fly.io, Railway, or VPS).

# Open Pickleball Tourney

## Active direction: browser edition (October 5)

Ryan selected one organizer using one computer/tablet. The active UI is the
Hugo static site in `site/`; start its development preview with `./play`.
Read `site/README.md` and the October 5 contract at the top of `spec.md`.
The existing Django application remains intact as a separate edition.

- Browser code: `site/assets/js/engine.mjs` (pure rules and backup validation),
  `storage.mjs` (locked browser saving), `app.js` (guided UI).
- Hugo: `site/layouts/home.html`, `home.serviceworker.js`, `site/hugo.toml`;
  readable CSS in `site/assets/css/style.css`. No npm install or external assets.
- Build: `hugo --source site --cacheDir "$PWD/site/.cache" --cleanDestinationDir --panicOnWarning`.
- Targeted browser checks only: `node --test site/tests/browser-rules.test.mjs`.
  Do not run the unrelated Django suite for static-only edits.
- Records belong to one browser/address; never claim shared editing or server
  backup. Saving failures must keep recoverable data and visibly report failure.
- Current scope is casual round robin, 2–16 entries, 1–8 courts, fixed singles
  or doubles, one game to 11/15/21 and win by two. No sanctioned-event claims.
- Static output is `site/public/` (ignored). `.github/workflows/pages.yml` is
  prepared to publish `site/` as the GitHub Pages micro site (the `docs/`
  showcase is no longer what it serves). It has never run: enabling Pages,
  pushing and triggering it are Ryan's actions, not an agent's.

## Existing Django edition

Local Django 5.2 / Python 3.13 app for adult community pickleball events. Read [README.md](README.md), [IMPLEMENTATION.md](IMPLEMENTATION.md) (evidence and limits) and [roadmap.md](roadmap.md) (next work); [spec.md](spec.md) documents its broader target scope (historical/advanced scope relative to the active browser edition).

- Run: `./tour` (isolated demo) or `./tour serve`. Python is `.venv/bin/python`.
- Tests: `.venv/bin/python manage.py test` is the whole suite (about 5 s). **Give Ryan this command and let him run it; do not run suites or `gitnexus analyze` in a session.**
- Layout: `engine.py` pure tournament logic; `services.py`/`operations.py` mutations via `@command` (event row lock, revision check, idempotency key, audit); `views.py`/`desk_views.py` thin HTTP; `portability.py` archives/CSV; `delivery.py` mail worker and maintenance.
- Mutations go through `@command`; never write event state directly from a view. Unvalidated model constraints that involve `event` need explicit form checks (ModelForm skips them).
- Boundaries: no `git add`/`commit`/`push`, deploy or publish unless Ryan names the action. GitHub Pages enablement and the license are his decisions. Keep docs honest: never mark R1/R2/R3 complete, claim provider approval, or call untested behavior verified.

@AGENTS.md

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **open-pickleball-tourney** (1024 symbols, 2666 relationships, 85 execution flows).

> Index stale? Run `node .gitnexus/run.cjs analyze --index-only` from the project root — it auto-selects an available runner. No `.gitnexus/run.cjs` yet? Bootstrap with `npx`, `bunx`, or `pnpm dlx` — e.g. `bunx gitnexus@latest analyze` (npm 11 npx crash; #1939).

## Always Do

- **MUST run impact before editing.** Use `impact({target: "symbolName", direction: "upstream"})` or `node .gitnexus/run.cjs impact "symbolName" --direction upstream --repo .`; report callers, processes, and risk. Never substitute grep for graph analysis.
- **MUST analyze graph changes before committing.** Use `detect_changes({scope: "all"})` (MCP) or `node .gitnexus/run.cjs detect-changes --scope all --repo .` (CLI fallback). `partial: true` or `truncated: true` is not a clean check — a zero means unseen, not unaffected; re-run it. For regression review: `detect_changes({scope: "compare", base_ref: "main"})` or `node .gitnexus/run.cjs detect-changes --scope compare --base-ref "main" --repo .`.
- MUST warn on HIGH/CRITICAL `risk` pre-edit; never use `riskSharedAxes` to waive a HIGH/CRITICAL `risk` warning. Compare File/symbol: MCP File omits axes; Graph-RAG expands File.
- **MUST treat `risk: UNKNOWN` as unresolved, not as low.** An empty caller set is not evidence the symbol is unused — it can also mean the callers are not resolvable by the index (plain-object property access, dynamic dispatch, cross-language calls). `impact` pairs `UNKNOWN` with a `riskNote` saying so. Confirm with a text search before treating the symbol as safe to change or delete; do not proceed on the strength of a zero.
- **MUST use `query({search_query: "concept"})` for concepts/flows, `context({name: "symbolName"})` for a named symbol, or `impact` for blast radius, on read-only callers, dependencies, imports, or execution flow.** Graph first; text search only for empty/`UNKNOWN`/literals.
- For security review, `explain({target: "fileOrSymbol"})` lists taint findings (source→sink flows; needs `analyze --pdg`).

## Never Do

- NEVER edit a function, class, or method before MCP/CLI impact analysis.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis, and never read `UNKNOWN` as an all-clear — it means the walk could not answer, which is the one verdict that requires confirming by other means.
- NEVER rename symbols with find-and-replace — use `rename` which understands the call graph.
- NEVER commit before MCP/CLI graph change analysis.

## Resources

| Resource | Use for |
| --- | --- |
| `gitnexus://repo/open-pickleball-tourney/context` | Codebase overview, check index freshness |
| `gitnexus://repo/open-pickleball-tourney/clusters` | All functional areas |
| `gitnexus://repo/open-pickleball-tourney/processes` | All execution flows |
| `gitnexus://repo/open-pickleball-tourney/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
| --- | --- |
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->

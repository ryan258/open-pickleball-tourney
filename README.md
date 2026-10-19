# Open Pickleball Tourney

> **Direction (October 18):** a joyful, phone-first tool for impromptu pickleball
> tournaments among friends and small clubs, not major events. The earlier Django
> edition is archived in [`django-edition/`](django-edition/) and is not maintained.

**This is a simple browser tournament desk for one organizer on a phone,
computer or tablet.** The Hugo site in [`site/`](site/) handles quick-start format recommendations,
step-by-step event setup, seven formats (round robin, round robin into playoffs, pool play into playoffs,
single elimination, double elimination with reset finals, rotating partners with fair rest rotations, and king/queen
court ladders), touch-friendly score stepper pads, display-board views, shareable results text, reviewed
scores, printable sheets, browser-local saving, and backup recovery. Fixed formats
support 2–16 singles players or doubles teams on 1–8 courts; social formats take 4–16
individuals (rotating partners supports late arrivals and early departures; the court
ladder needs exactly four players per court). No accounts or remote data services.

For a local development preview:

```sh
./play
```

Open [localhost:1313](http://localhost:1313/). Use **Quick start** on the home screen to paste names and get an instant format recommendation matching your group and court time; **Try a practice tournament** to explore a ready-to-play example in your chosen format; or **Start a tournament** for full step-by-step setup. `./play`
is a maintainer command using the installed Hugo. Once the site is hosted,
organizers will only need its address and a browser. The intended home is a
GitHub Pages micro site, updated by pushing changes to `main` (see
`.github/workflows/pages.yml`), with a downloadable offline copy for organizers
who prefer a double-click or a screen/board computer. **This work is local; Pages is not enabled and
the browser edition has not been published.**

Tournament records stay in the same browser and website address. Download a copy
before clearing browser data, changing addresses/devices, or starting a new
event. A production static
build can reopen offline after its footer confirms that caching succeeded;
the Hugo development preview does not install the offline worker.

See [`site/README.md`](site/README.md) for the bounded workflow, local build,
targeted checks, and recovery behavior. [IMPLEMENTATION.md](IMPLEMENTATION.md)
records evidence and limits; [roadmap.md](roadmap.md) records the active direction.
The [101 rules questions and answers](docs/101-really-good-pickleball-rules-questions-w-answers.md)
guide compares the 2026 rulebook with this app's casual house rules.

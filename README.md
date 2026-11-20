# Aircraft Maintenance Platform

Tagup take-home exercise: track aircraft write-ups from report to repair, and show at any moment which aircraft are cleared to fly.

The decisions behind it, what was left out and what would come next are in [DECISIONS.md](DECISIONS.md).

## Run it

The only thing to install is [uv](https://docs.astral.sh/uv/getting-started/installation/). It fetches Python 3.12 and the dependencies on the first run.

```bash
uv run python -m app
```

Then open http://127.0.0.1:8000.

The first run creates `maintenance.db` (SQLite) in the project folder and fills it with a demo fleet. There are no external services and nothing to configure. The app uses port 8000, so that port must be free.

To wipe the database and start again from the demo fleet:

```bash
uv run python -m app --reset
```

To run the tests:

```bash
uv run pytest
```

## Try it out

The demo fleet has 30 aircraft, N401TG to N430TG. The first twelve each show one situation; the rest have no write-ups. Dates are relative to the day the database was seeded.

1. **Read the board.** Four aircraft are grounded and 26 are cleared. Each row lists the aircraft's open write-ups with their severity and due date. Search by tail number, or hide a group with its Hide link.
2. **Clear an aircraft.** Open N403TG. It is grounded by one High write-up that is in progress and overdue. Press Resolve, say what was done and who you are, and it moves to Cleared.
3. **See that one fix isn't always enough.** N404TG has two High write-ups. Resolve the one in progress and the aircraft stays grounded.
4. **Take a write-up from report to repair.** N401TG has a High write-up nobody has scheduled. Schedule it, start work, then resolve it. Each step asks for a name and lands in the History list below the cards.
5. **Ground an aircraft.** Open any aircraft from N413TG up, press Create write-up and file a High. It moves to Grounded straight away. A Medium or Low doesn't ground it.
6. **Change a write-up in place.** On a card, the severity, the due date and the description are each the control that changes them. Downgrading N402TG's High to Medium, with a reason, clears the aircraft.
7. **Look at the other ways an aircraft got cleared.** N406TG's High was downgraded after inspection, N407TG's was canceled as no fault found, and N408TG is cleared despite an overdue Medium. The History list shows who did what and why.
8. **Act from an out-of-date page.** Open the same aircraft in two tabs. Change a write-up in one, then try to act on it in the other: the action is refused with a message and the card shows the current state.

## What's in the repository

- `app/rules.py`: the rules as plain functions, with no database or web code: what grounds an aircraft, which status changes are allowed, what counts as overdue.
- `app/service.py`: each action (file, schedule, start, resolve, cancel, change severity, edit description) applied to the database with its audit entry, plus the queries behind the board and the history.
- `app/models.py`, `app/db.py`: the tables and their constraints.
- `app/main.py`: the routes and error handling.
- `app/templates/board.html`, `app/static/`: the one page, its stylesheet and a small script that keeps the board's scroll position.
- `app/seed.py`: the demo fleet, built through the same actions the app uses.
- `tests/`: unit tests for the rules, and tests through the routes on a fresh database per test.
- `CLAUDE.md`: the working instructions given to the AI coding agent.

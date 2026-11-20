# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Backend is fixed by DECISIONS.md A1–A5: FastAPI, server-rendered HTML templates, plain forms that redirect after each POST, SQLite, one `uv run` command.

Frontend: one hand-written CSS file, zero JavaScript, no build step. Disclosure uses native HTML (`<details>`, separate pages); every action is a form POST.

## Users

Pilots, mechanics and maintenance control at one airline, all sharing one view with no roles and no login. They type their name on every action.

- Maintenance control works from a desktop monitor and is the main seat the UI is designed for.
- A pilot or mechanic may use a phone on the ramp or in the hangar to file a write-up or move one along. That must work, but is not optimized ahead of the desk.

## Product Purpose

Track aircraft write-ups from report to repair and show, at any moment, which aircraft are cleared to fly and which are not.

Success: anyone opening the app can tell within seconds what can fly, what cannot, and why each grounded aircraft is grounded; and every write-up has a complete, trustworthy history of who changed what and when.

## Positioning

An internal operations tool, not a product sold to anyone. Its claim is correctness: clearance is computed from open write-ups on every page load and never stored, so it cannot drift from the record, and every change carries a name and an audit entry.

## Operating Context

- Home screen is the fleet clearance board. Showing what cannot fly is as important as showing what can: grounded aircraft and the High write-ups grounding them are explicit, and cleared aircraft are stated as cleared rather than implied by absence.
- Filing and acting on write-ups happens from an aircraft's page.
- Status is correct whenever a page loads or an action is taken. Other users' changes appear on refresh; there is no live push.
- Fleet of about 30 aircraft, but screens must still work at 300–1,500 aircraft.

## Capabilities and Constraints

Terminology and rules (full detail in DECISIONS.md):

- **Write-up:** a free-text defect description against one aircraft, with severity High, Medium or Low.
- **Status:** Unscheduled → Scheduled → In progress → Resolved, plus Canceled from any open state. Scheduled can go back to Unscheduled; In progress cannot go back. Resolved and Canceled are final and read-only.
- **Scheduled date:** the date the repair should be finished by. Never in the past. Editable while Scheduled or In progress.
- **Grounded:** any open High write-up grounds its aircraft. Medium and Low never ground.
- **Overdue:** an open write-up past its scheduled date. A computed flag; it does not affect clearance.
- Every action requires a name. Resolve, cancel and severity change also require a note. A change that changes nothing is rejected with a message.
- Full audit log per write-up: who, when, old and new value, note.
- Fleet is seed data; aircraft cannot be added or edited in the UI. MEL deferrals are out of scope.
- Time budget for the whole exercise is about two hours; the UI should be a focused set of screens done well.

## Brand Commitments

None. No product name, logo or airline identity has been chosen; the working title is "Aircraft Maintenance Platform".

## Evidence on Hand

- Demo fleet of 30 made-up aircraft in `app/seed.py`, built through the app's own actions. The first twelve each demonstrate one situation (grounded in each open state, grounded by two Highs, cleared after a fix, after a downgrade, after a no-fault cancel, cleared despite an overdue Medium, and so on).
- No real airline, people, tail numbers or operational data. Do not invent claims about real operators.

## Product Principles

1. **Answer "can it fly?" first.** Every screen that shows an aircraft shows its clearance, stated both ways: grounded and cleared are each explicit.
2. **Show the reason, not just the verdict.** A grounded aircraft always points to the write-ups grounding it.
3. **The record is the truth.** Nothing on screen is a cached or derived state that could disagree with the write-ups and audit log.
4. **Every change has a name on it.** Actions ask for who and, where required, why; history is visible, not hidden.
5. **Boring and dependable over clever.** Plain forms, plain pages, no script required for anything.

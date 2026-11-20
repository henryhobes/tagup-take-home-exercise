# Decisions

## Questions for the product manager

### 1. Can a write-up be filed without a repair date?
**Decision:** Yes. A write-up can be filed without a date and starts as Unscheduled.

### 2. What stages does a write-up move through?
**Decision:** Unscheduled → Scheduled → In progress → Resolved.
**Note:** Went against the AI recommendation, which was to leave out In progress.

### 3. Does a fix need a separate inspection or certification sign-off?
**Decision:** No separate stage. Resolving a write-up records who fixed it and what was done.

### 4. Can a resolved write-up be reopened?
**Decision:** No. A recurring defect is filed as a new write-up.

### 5. Who are the users, and do views differ by role?
**Decision:** One shared view for pilots, mechanics and maintenance control, with no roles and no login. People type their names where it matters (reporter, fixer).

### 6. Who is a write-up assigned to?
**Decision:** Nobody. A scheduled date is enough, and the fixer's name is recorded when the write-up is resolved.

### 7. Do we store and display a history of who changed what and when?
**Decision:** Yes, a full audit log of every change to each write-up.
**Note:** Went against the AI recommendation, which was to store only key timestamps on the write-up itself.

### 8. Any categorization besides severity and status?
**Decision:** No. The defect is a free-text description.

### 9. How many aircraft and live write-ups should the app handle?
**Decision:** Designed for a fleet of about 30 aircraft, but it shouldn't fall over if the fleet grew 10x to 50x (roughly 300 to 1,500 aircraft).
**Note:** Went further than the AI recommendation, which was to design only for a small fleet and accept that scaling later would need rework.

### 10. What decides whether an aircraft is cleared to fly?
**Decision:** Any unresolved High write-up grounds the aircraft, from the moment it's filed until every High on that aircraft is resolved. Medium and Low never ground, even when overdue. Cleared status is computed from open write-ups, never stored.

### 11. Can severity be changed after filing?
**Decision:** Yes, but changing it requires a name and a reason, which are recorded in the audit log. Grounding is recalculated immediately.

### 12. Does "at any moment" mean live push updates?
**Decision:** No. Status is correct whenever a page loads or an action is taken. Other users' changes appear on refresh.
**Why:** Start simple. If there's time at the end, add live push then.

### 13. How does a write-up close when there's no fault to fix, or it's a duplicate?
**Decision:** A separate Canceled state, with a required note. This adds to the stages in question 2.
**Note:** Went against the AI recommendation, which was to reuse Resolved with a note.

### 14. What happens when a scheduled repair date passes?
**Decision:** The write-up is flagged Overdue. That flag is computed and doesn't affect whether the aircraft can fly.

### 15. Can aircraft be added or edited in the app?
**Decision:** Not for now; the fleet is seed data. Managing aircraft in the UI is a candidate to pick up at the end if there's time.

### 16. Should the app model MEL deferrals?
**Decision:** No, that's out of scope.

### 17. Can an Unscheduled write-up go straight to In progress?
**Decision:** No. It must be Scheduled first.

### 18. Once Scheduled, can the date change or the write-up go back to Unscheduled?
**Decision:** Both. The date can be changed, and a Scheduled write-up can go back to Unscheduled.
**Note:** Went against the AI recommendation, which was to allow rescheduling only.

### 19. Can an In progress write-up go back to Scheduled (e.g. waiting on parts)?
**Decision:** No. It stays In progress, but its scheduled date can still be changed. The scheduled date is the date the repair should be *finished by*, not the day work starts. A multi-day repair might go In progress on Monday with a scheduled date of Friday.
**Note:** Went against the AI recommendation, which was to allow going back to Scheduled with a new date.

### 20. Can a write-up be Resolved directly from Scheduled?
**Decision:** No. Only an In progress write-up can be Resolved.

### 21. Which states can a write-up be Canceled from, and what does it require?
**Decision:** Any open state (Unscheduled, Scheduled, In progress). Canceling requires a name and a note, the same as a severity change, because canceling an open High clears the aircraft. This adds the name to question 13.

### 22. Can the scheduled date be set to a date in the past?
**Decision:** No. Dates before today are rejected, both when scheduling and when rescheduling.

### 23. Can a write-up's description or aircraft be edited after filing?
**Decision:** The description can be edited, and each edit is recorded in the audit log. The aircraft can't be changed; a write-up filed against the wrong aircraft is canceled and filed again.
**Note:** Went against the AI recommendation, which was to allow no edits.

### 24. Can a resolved or canceled write-up still be edited?
**Decision:** No. Severity and description can only change while a write-up is open. Closed write-ups are history.
**Note:** Made during implementation, not yet reviewed.

### 25. What happens when a change doesn't change anything (same date, same severity, same description)?
**Decision:** It's rejected with a message, so the audit log never holds entries where nothing happened.
**Note:** Made during implementation, not yet reviewed.

### 26. Where is the app used: at a desk or on the ramp?
**Decision:** Designed for maintenance control at a desktop monitor first. A pilot or mechanic on a phone can still file and act on write-ups, but the phone layout isn't optimized ahead of the desk.

### 27. What does the home screen show?
**Decision:** The fleet clearance board. Grounded and cleared are both stated explicitly, and each grounded aircraft shows the High write-ups grounding it. Filing and acting on write-ups happens on an aircraft's page.
**Why:** The brief's core promise is showing which aircraft are cleared to fly. What can't fly matters as much as what can, so neither state is left to be inferred.

### 28. How is the fleet board laid out?
**Decision:** One table with two row groups, Grounded first, then Cleared, each with a count and an explicit empty message. Each group can be hidden or shown; both start shown. Every row lists all its open write-ups, Highs first, each behind a fixed-width severity label, plus Overdue and Needs scheduling markers. Within each group, overdue first, then needs scheduling, then earliest scheduled date, then tail number.
**Why:** Started as two separate sections with each aircraft's Highs listed inline. Once aircraft details moved into a sidebar (29), the inline lists weren't needed and would have been cramped, so one table keeps columns aligned and the phone layout trivial. A Needs scheduling marker is there because the brief says every issue needs scheduling, and an unscheduled Medium would otherwise be invisible on the board. Listing every open write-up replaced an open-count column; the fixed severity column keeps a wrapped description from reading as a second write-up. Hiding a group lets a large Cleared list get out of the way. Which groups are hidden, like the search, lives in the URL and rides along on every link and form, so it survives opening aircraft and taking actions.
**Note:** Rows used to repeat Grounded or Cleared next to each tail. The group heading already states it for every row under it, so the repeat was dropped and the row leads with the write-ups. The aircraft panel still states clearance on its own.

### 29. Where are an aircraft's details?
**Decision:** Selecting an aircraft opens a sidebar beside the board on desktop. On a narrow screen the same URL shows only the aircraft, with a link back to the fleet. The panel holds the clearance status, a Create Write-Up button, one card per open write-up with its actions, and one timeline of every event across all of that aircraft's write-ups. Closed write-ups appear only in the timeline. Tail-number search on the board is a plain GET form.
**Why:** One URL and one template serve both layouts without JavaScript (A13). A single timeline per aircraft answers "what happened to this plane" better than a history per card.
**Note:** Searching, and clearing a search, keep the open aircraft's panel. They first closed it, the only controls on the board that did; the panel now closes only from its own Close link.

Each write-up card is edited in place: the severity, the date and the description are each the control that changes them, opening a small form where they sit. The card's one button is the next step for its status (Schedule, Start work or Resolve), and Cancel is a quiet link. Status is a muted chip; the date, or Needs scheduling, sits in the top-right corner. A first version put every action in a list of disclosures under each card, which read as a settings page rather than a work item.

### 30. How is a write-up filed?
**Decision:** From a Create Write-Up button in the aircraft panel, with the form shown inline in the panel. A modal is a later polish item, only if time remains. Severity has no default; the reporter must choose. A scheduled date can be given while filing; the write-up is then filed and scheduled in one step, and the audit log records the reporter as the one who scheduled it.
**Why:** The button lives where the aircraft is already known, so the existing per-aircraft route works unchanged. A preselected severity would let someone file a grounding defect as Medium by accident.

### 31. What does the app look like?
**Decision:** Tagup's own design language from tagup.ai: Barlow for text, IBM Plex Mono for labels and data, square corners, and their dark palette only. Orange means caution only (Overdue, Needs scheduling); Grounded uses their danger red and Cleared their green; buttons are neutral.
**Why:** It's a Tagup exercise. On a clearance board color has to mean status, so the brand orange can't also mark buttons.
**Note:** Four kinds of label, each with one look. An aircraft's clearance (in its panel) is a filled chip in its color; a write-up's status is a muted chip; Overdue and Needs scheduling are orange outlined chips; severity is bare text. Clearance started as bare red text and read the same as a High severity label beneath it. All chips share one box: trimmed to the capital height with equal insets, so they line up on the text baseline next to them.

## Architecture

### A1. Language and framework?
**Decision:** Python with FastAPI.
**Why:** Small and explicit. Pydantic validates input at the boundary, and pytest with TestClient makes route tests easy. Django brings more ceremony than this needs; TypeScript only pays off with a separate JS frontend.

### A2. Server-rendered pages or a separate JS app?
**Decision:** Server-rendered HTML templates with plain forms, redirecting after each POST.
**Why:** One process, one language, nothing to build. Decision 12 only needs status to be correct on page load, so a single-page app's extra toolchain buys nothing.

### A3. Database and how we talk to it?
**Decision:** SQLite through SQLAlchemy. Tables are created on startup; no migration tool.
**Why:** No setup for the reviewer, and SQLite easily handles 1,500 aircraft. A transaction makes each change and its audit entry commit together. A schema change means deleting the DB file and reseeding, which is fine for a demo.

### A4. What shape are the routes?
**Decision:** One POST route per action (schedule or reschedule, unschedule, start, resolve, cancel, change severity, edit description), each with its own required fields and its own audit entry. No JSON API.
**Why:** Each action has different rules and inputs, so separate routes keep validation explicit. A generic edit route would have to infer what happened. Nothing in the brief needs JSON.

### A5. How does someone run it?
**Decision:** One `uv run` command. It seeds demo data when the database has no aircraft; a reset command wipes and reseeds.
**Why:** uv fetches the right Python and dependencies itself, which avoids the most common way take-homes fail to start. No external services.
**Note:** Seeding first keyed on the DB file not existing. The tables are created before the seed runs, so a first run that was interrupted left a file with an empty fleet that no later run would fill.

### A6. How is testing set up?
**Decision:** pytest in two layers. Unit tests on plain Python rule functions (transitions, grounding, overdue, date checks), written first. Route tests through TestClient on a fresh SQLite database per test. No browser tests; the UI is checked by hand.
**Why:** Rules get fast, pinpointed tests for TDD; route tests cover what only exists with a database (audit entries, validation errors, the fleet page). Browser tests are a time sink at this scope.

### A7. Where is "cleared to fly" computed?
**Decision:** In one Python rule function. The fleet page loads all open write-ups in one query, groups them by aircraft, and applies it.
**Why:** One source of truth that the unit tests cover. At 1,500 aircraft that's milliseconds. At far larger scale it would move into SQL.

### A8. What counts as "today" for Overdue and past-date checks?
**Decision:** The server's local date. Scheduled dates are calendar dates with no time. Today is passed into the rule functions so tests can fix it. Audit timestamps are stored in UTC.
**Why:** Simple and predictable. An airline spanning time zones could disagree about "today" near midnight; per-base time zones would fix that but aren't worth it here.
**Note:** Audit timestamps are shown in the server's zone at the offset it had on that date. They were first converted with today's offset, which put entries from the other side of a daylight-saving change an hour out. The test for this sets the process time zone, which Windows can't do, so it is skipped there.

### A9. Where do "who" and "why" live, and who has to give a name?
**Decision:** The write-up row holds its current state plus who filed it and when. Every later change is an audit-log row with who, when, the old and new value, and a note. A name is required on every action, not only filing and resolving. Who fixed it and what was done live only on the resolve entry; cancel notes and severity reasons likewise.
**Why:** Decision 7 promises a history of who changed what, which needs a name on every change. This extends decision 5. Keeping each fact in one place avoids resolution columns on the write-up that duplicate the log.
**Note:** The row holds only the current severity, so the History line "Filed as …" takes the severity at filing from the log: what the first severity change replaced, or the current one if it never changed. It first printed the current severity, which was wrong after a downgrade. Storing a second severity column or logging a filing entry would duplicate what the log already says.

### A10. How much is enforced by the database itself?
**Decision:** Foreign keys are enforced (SQLite leaves them off unless every connection turns them on). CHECK constraints cover: allowed severity, status and audit-entry values; non-empty names and descriptions; the scheduled date matching the status (empty when Unscheduled; set when Scheduled, In progress or Resolved; either when Canceled, since a write-up can be canceled before it was ever scheduled); and a note on every resolve, cancel and severity change.
**Why:** A second line of defense against bad seed data, manual edits and future bugs. This is a deliberate exception to CLAUDE.md's "don't guard against impossible states". Two rules stay in code only: which transitions are allowed (a CHECK sees one row, not the previous state) and no dates in the past (SQLite rejects `date('now')` in a CHECK constraint).

### A11. How is the seed data built?
**Decision:** Through the same actions the app uses, run with backdated clocks, rather than inserted rows. 30 aircraft; the first twelve each demonstrate one situation (grounded in each open state, grounded by two Highs, cleared after a fix, after a downgrade, after a no-fault cancel, cleared despite an overdue Medium, and so on). A test fails if the seed stops covering every status, severity, audit entry type, overdue case and aircraft situation.
**Why:** Seeded write-ups and audit entries are guaranteed to be ones the app could produce, and the demo can't silently lose a case.

### A12. Indexes?
**Decision:** Write-ups are indexed on (aircraft, status) for an aircraft's page and on status for the fleet page's "all open write-ups" query. Audit entries are indexed on write-up.
**Why:** The fleet page filters by status alone, which the (aircraft, status) index from the reviewed model can't serve.

### A13. How much frontend tooling?
**Decision:** One hand-written CSS file. Disclosure uses native HTML (`<details>`, separate pages). One small script keeps the board's scroll position across page loads; nothing depends on it.
**Why:** Follows from A2. Every action is a plain form POST, so a script would add a second way for things to break. The exception: every click loads a new page, and without a script the board jumped back to the top each time, which made a long fleet list unusable. The script only restores the scroll position; with it off, every action still works.
**Note:** Started as zero JavaScript; changed after trying the board.

### A14. What does someone see when they act on a write-up that changed under them?
**Decision:** The action is rejected and the reason shows at the top of the aircraft panel, prefixed with which write-up changed. Other rejections (a blank name, a past date) still show inside the form that was submitted.
**Why:** The card only offers the actions its status allows, so a status rejection means the page was out of date (someone else acted, or a double submit), and by then the submitted form is no longer on the card. The message used to be attached to that missing form, so the page came back as a 400 with no explanation. Status rejections are their own exception type so the route can tell the two cases apart without knowing which forms each status shows.

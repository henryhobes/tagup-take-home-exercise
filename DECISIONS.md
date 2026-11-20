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

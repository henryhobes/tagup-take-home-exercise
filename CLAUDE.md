# CLAUDE.md

Tagup take-home: an aircraft maintenance tracker. The brief is `tagup-take-home-exercise.pdf` (gitignored). Time budget is about two hours.

## Principle

Keep it simple. Boring code that works beats clever code. Don't get ahead of the task.

## Code

- No abstraction until the same thing is needed in two places.
- Almost no comments. A comment explains *why*, never *what*. If a better name would make a comment unnecessary, rename instead.
- Don't swallow errors. No catch-and-ignore, no silent fallbacks, no defaults that hide a bug. If something breaks, surface it so it gets fixed properly.
- Validate at real boundaries (user input, external data). Don't guard against states the code itself makes impossible.

## Workflow

- TDD: write the test first, watch it fail, then implement.
- Run the tests before saying anything is done, and report the actual result.
- Never weaken, skip, or delete a test to make it pass. If a test looks wrong, stop and say so.
- Commit each time something goes green.

## Scope

- Do what was asked and nothing more. If you notice something else (a bug, an improvement, a missing feature), flag it instead of doing it.
- Write every judgment call down in `DECISIONS.md`: the question, the call, and why.

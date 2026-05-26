# Agent Instructions

## Session Start

At the beginning of every session, before doing anything else:
1. Read all skills from `.github/skills/` directory (each subfolder contains a `SKILL.md` file).
2. Keep the skills in mind throughout the session and apply them automatically at the right moment.

## Skills

Skills are located in `.github/skills/`. Each skill defines **when** and **what** to do:

- **`run-tests`** — run after any code changes and before considering a task done.
- **`write-tests`** — run after completing a new feature, before `run-tests`.

## General Rules

- Always apply the relevant skill automatically — do not wait for the user to ask.
- If tests fail, fix the issues and re-run before reporting success.
- Use `python -m unittest discover -s tests -p "test_*.py"` to run tests.

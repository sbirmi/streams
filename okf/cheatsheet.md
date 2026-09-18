# Cheatsheet

## Before changing code

1. Read `AGENTS.md` and the relevant `okf/` documents.
2. Identify whether the change affects requirements, behavior, data, deployment, or security.
3. Update the affected documentation in the same change.

## Development and tests

- Use the project-local virtualenv for application commands and tests.
- Run the repository’s standard test command; it must invoke the virtualenv automatically when needed.
- Do not install project dependencies into or rely on the global Python environment.

## Core behavior

- Notes are short, shared, and thread-like.
- Comments/updates are append-oriented.
- Note writes use a revision precondition.
- A stale write must produce a visible conflict, never a silent overwrite.
- URL access currently implies trusted read/write access.

## Release checklist

- Tests cover create/read/update/append and stale-write conflicts.
- Documentation matches the current API, data model, configuration, and deployment.
- Dependencies and lockfile changes were reviewed.
- Backup and restore were verified for the release.
- No secrets or unnecessary note content appear in logs.

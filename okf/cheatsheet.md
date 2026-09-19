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
- Deletion requires confirmation and a current revision; stale deletes produce the same visible conflict response.
- URL access currently implies trusted read/write access.
- Stream owners are entered as comma-separated names; whitespace-only entries are omitted. Deadlines use `YYYY-MM-DD` and are shown as `due YYYY-MM-DD`.
- Stream tags are entered as comma- or whitespace-separated values; empty values are omitted and the remaining order is preserved.
- Sibling order is stored in a server-controlled numeric `order_key`, allocated with gaps and shown read-only in the stream modal. Clients must not submit it as an editable stream field.
- The View selector offers Priority, Recently touched, Manual order, and Stale. Manual order renders siblings by `order_key`.
- Permalinks use `root=<stream-id>`, `view=priority|recent|manual|stale`, and `focus=stream:<stream-id>` or `focus=comment:<comment-id>`. Omit `root` for the index; local expansion and presentation state remain client-side per bundle/root, independent of sort mode.

## Release checklist

- Tests cover create/read/update/append and stale-write conflicts.
- Documentation matches the current API, data model, configuration, and deployment.
- Dependencies and lockfile changes were reviewed.
- Backup and restore were verified for the release.
- No secrets or unnecessary note content appear in logs.

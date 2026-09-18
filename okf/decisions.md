# Decisions

## D001 — Documentation is the source of truth

- **Status:** accepted
- **Decision:** Maintain project knowledge, requirements, design, operations, and decisions in this `okf/` bundle. Update it alongside code and configuration.
- **Reason:** The project is expected to evolve through discussion, and implementation should not become the only record of behavior.

## D002 — Trusted-network, shared-access initial model

- **Status:** accepted for initial scope
- **Decision:** Do not require individual accounts initially; network URL access implies trusted read/write access.
- **Reason:** The service is intended for a secure internal network and should remain simple.
- **Constraint:** This is not approval for public exposure. The security model must change before that.

## D003 — Optimistic concurrency for note edits

- **Status:** proposed baseline
- **Decision:** Use revision-checked writes for whole-note edits and atomic append operations for comments/updates.
- **Reason:** It prevents silent clobbering while keeping the application simple and avoiding locks.

## D004 — Flask, SQLite, and a thin browser client for the initial implementation

- **Status:** accepted for initial implementation
- **Decision:** Use Flask with Python, SQLite through `sqlite3`, server-rendered HTML, vanilla JavaScript, and project-owned CSS. Run application and tests through the project-local virtualenv.
- **Reason:** This keeps the first implementation small, fast to start, and easy to inspect while leaving room for targeted client-side behavior.

## D005 — SQL migrations and repository-owned transactions

- **Status:** accepted for initial implementation
- **Decision:** Keep schema changes as ordered SQL migrations. A repository layer owns SQL and short SQLite transactions; routes and future services do not manage raw connections directly.
- **Reason:** This keeps the data boundary explicit, makes upgrades reviewable, and supports revision checks/history without coupling the UI to SQLite details.

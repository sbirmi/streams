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


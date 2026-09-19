# Project guidance

## Source of truth

The `okf/` directory is the project knowledge bundle and is the source of truth for this project. It contains the product intent, requirements, design notes, operational documentation, and decisions.

Before making a code or configuration change:

1. Read the relevant material in `okf/`.
2. Update the documentation in the same change whenever behavior, interfaces, operations, security posture, or a decision changes.
3. If the change introduces an unresolved product or technical choice, record it in `okf/decisions.md` or `okf/open-questions.md`.
4. Keep examples and deployment instructions executable and aligned with the implementation.

When documentation and code disagree, treat the discrepancy as a bug. Resolve it before considering the work complete.

## Product context

This is intended to be a small, fast web notes application for ideas, issues, threads, and conversation updates. It runs inside a trusted network, supports multiple people reading and writing shared data, does not initially require individual accounts, and must prevent accidental clobbering during simultaneous edits.

## Engineering priorities

- Keep the system simple and fast.
- Develop and test inside the project virtualenv; test commands should activate or invoke that environment automatically rather than relying on a developer’s global Python installation.
- Minimize dependencies and pin or otherwise review dependencies to reduce supply-chain risk.
- Make concurrent edits safe and visible; never silently overwrite a newer change.
- Prefer reversible, observable operations and documented defaults.
- Do not add authentication, authorization, or internet exposure assumptions without documenting the change.

## Development workflow

- Keep the primary chat session focused on planning, discussion, review, and coordination.
- Do not use the primary chat session for development work when a subagent can perform it.
- Delegate implementation, investigation, testing, and other development tasks to subagents whenever practical so the primary session’s context remains available for planning and discussion.

## Documentation map

- Start with [`okf/README.md`](okf/README.md).
- Current implementation queue: [`TODO.md`](TODO.md).
- Product intent and scope: [`okf/product.md`](okf/product.md).
- Requirements and acceptance criteria: [`okf/requirements.md`](okf/requirements.md).
- Initial design: [`okf/architecture.md`](okf/architecture.md).
- Concurrency model: [`okf/concurrency.md`](okf/concurrency.md).
- Security and supply-chain posture: [`okf/security.md`](okf/security.md).
- Deployment and operations: [`okf/deployment.md`](okf/deployment.md).
- Quick reference: [`okf/cheatsheet.md`](okf/cheatsheet.md).
- Decisions and unresolved topics: [`okf/decisions.md`](okf/decisions.md), [`okf/open-questions.md`](okf/open-questions.md).

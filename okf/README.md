# Project knowledge bundle

This directory is the project’s open knowledge foundation (OKF) bundle: a small, reviewable set of Markdown documents covering what we are building, why, how it should work, and how it is operated.

Documentation is the source of truth. Every implementation change must update the relevant bundle documents in the same change, or explicitly state why no documentation is affected.

## Contents

| Document | Purpose |
| --- | --- |
| [Product](product.md) | Intent, users, scope, and guiding principles |
| [Requirements](requirements.md) | Initial functional and non-functional requirements |
| [Architecture](architecture.md) | Proposed system shape and data model |
| [UI](ui.md) | Minimal interaction model, views, and keyboard navigation |
| [Keyboard navigation](keyboard-navigation.md) | Focus model and proposed keyboard shortcuts |
| [Concurrency](concurrency.md) | Shared editing and conflict handling |
| [Security](security.md) | Trust boundary and supply-chain/security baseline |
| [Integrations](integrations.md) | Configurable external-reference recognition and rendering |
| [Deployment](deployment.md) | Deployment guide and operational expectations |
| [Cheatsheet](cheatsheet.md) | Fast reference for contributors and operators |
| [Decisions](decisions.md) | Decisions already made and their rationale |
| [Open questions](open-questions.md) | Topics deliberately left for future discussion |

## Status

This is a starting point, not a final specification. Items marked “proposed” or listed as open questions should be confirmed as the product develops.

The active implementation queue is maintained in the repository root [`TODO.md`](../TODO.md). Completed items are moved to the bottom of that same file.

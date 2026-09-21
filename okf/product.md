# Product intent

## Summary

Build a simplistic, fast, web-based notes application for keeping track of ideas, issues, threads, and conversation updates. Notes are generally short and are expected to evolve through comments or updates rather than become long documents.

## Users and environment

- The app is used by multiple people inside a secure network.
- Anyone who can reach the service URL is currently treated as a trusted user.
- Individual accounts are not part of the initial scope.
- Users may enter an unvalidated display username for attribution.
- Multiple users may read and write the same data at the same time.

The trusted-network assumption is an operating constraint, not a claim that the application is safe to expose directly to the public internet.

## Desired qualities

- Opens quickly and remains responsive on a modest internal deployment.
- Uses a minimal, information-dense interface rather than a dashboard-heavy layout.
- Makes it easy to add a note, append an update, and find an existing thread.
- Supports keyboard-first navigation and common actions.
- Keeps the data understandable and exportable.
- Makes concurrent changes explicit rather than silently losing someone’s work.
- Has a small dependency and operational footprint.

## Core interaction idea

The primary view is a compact hierarchy: a topic contains streams/issues, and each stream can show its latest comment or a configurable number of recent comments. Expanding a stream reveals its details and child items. The same underlying data should support alternate views such as priority/deadline, last update, and stale items.

The application can contain many independent bundles of streams: for example, todos, recipes, side projects, or any other collection of related thoughts. These are use cases of the same generic structure, not separate first-class features or schemas.

Descriptions and comments support Markdown and render safely. Stream summaries remain plain text so compact hierarchy labels, rows, and breadcrumbs do not become rich content.

Rendered descriptions and comments may contain ordinary hyperlinks and built-in or configured reference links. The application provides copy-link/copy-ID affordances for streams and comments so users can insert stable references into other items.

## Lightweight attribution

The root page should provide a place for a user to enter a made-up username. The application can use that value as the default creator/commenter attribution and wherever an owner/assignee value is needed. It is intentionally not validated and is not an authentication mechanism.

Creation and ownership are separate concepts: the person who creates a stream or comment is not necessarily the person responsible for owning or completing it.

## Initial non-goals

- Per-user identity, permissions, or audit attribution.
- Rich document editing or large knowledge-base authoring.
- Public internet exposure.
- Notifications and workflow automation before the core model is stable.
- A large visual editor or real-time co-editing experience.

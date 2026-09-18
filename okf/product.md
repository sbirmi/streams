# Product intent

## Summary

Build a simplistic, fast, web-based notes application for keeping track of ideas, issues, threads, and conversation updates. Notes are generally short and are expected to evolve through comments or updates rather than become long documents.

## Users and environment

- The app is used by multiple people inside a secure network.
- Anyone who can reach the service URL is currently treated as a trusted user.
- Individual accounts are not part of the initial scope.
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

Topics are expected to have their own “recipe” or presentation rules. For example, a recipe topic may show a dish as the top-level item and ingredients/steps beneath it, while a todo topic may emphasize priority and deadlines.

The interface should support Markdown in descriptions, summaries, and comments, rendered safely.

## Initial non-goals

- Per-user identity, permissions, or audit attribution.
- Rich document editing or large knowledge-base authoring.
- Public internet exposure.
- Notifications and workflow automation before the core model is stable.
- A large visual editor or real-time co-editing experience.

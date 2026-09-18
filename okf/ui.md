# User interface direction

Status: proposed.

The UI should optimize for fast rendering, low interaction cost, and information density. It should feel like a quick shared workbench, not a large project-management dashboard.

## Primary hierarchy

A topic can present streams/issues and their recent comments in a compact tree. A conceptual example:

```text
Topic 1

+ Issue 1  -> Most recent comment 1  -> [Older comment 2]
  + Issue 1 item 1
  + Issue 1 item 2
+ Issue 2
```

The actual stream row may also show priority, status, tags, creation date, last-update date, deadline, snooze date, or close date. Details should be progressively disclosed so the common view stays compact.

The number of recent comments shown per stream should be configurable per view or topic recipe: one, two, N, or none. “Show more” must reveal older comments without losing the current position.

## View recipes

Views should work at any hierarchy level: a topic, a selected parent stream, or the whole collection. Closed items should be excluded by default, with an option to include them.

### Default view: priority

The default view is a tree-oriented priority view:

1. Open items appear first.
2. Open items are grouped by priority, with P0 highest.
3. Within a priority group, the secondary ordering is still to be decided: deadline-first or most-recently-updated-first.
4. Closed items may be shown optionally, after open items.

### Deadline-first view

Show open items ordered by deadline, either as a flat list or while retaining the hierarchy. Items without deadlines need a defined placement, likely after dated items.

### Chronological view

Show items by most recently touched first. This is useful for finding active conversations and recent updates, and may be available as either a flat list or a tree-preserving view.

### Stale-open view

Show open items with no recent updates first, ordered by staleness. The meaning of “stale” and its threshold remain configurable or unresolved.

## Example alternate views

- Topic-specific recipes such as recipes (dish → ingredients/steps) or todos (item → status/priority/deadline).

Views should have stable, shareable URLs. A URL may identify a stream directly or encode a topic, ordering, filters, expansion state, and comment-count preference.

## Keyboard-first actions

The eventual shortcut set should cover:

- moving between visible streams/comments
- opening and closing a stream
- expanding/collapsing a topic or stream
- creating, editing, and moving an item
- adding a comment
- marking an item done/closed
- showing more comments
- jumping to search or a saved view

Exact keys, discoverability, focus behavior, and customization remain open. Shortcuts must not interfere with normal text entry in Markdown fields.

## Rendering and feedback

- Render Markdown for summaries, descriptions, and comments with safe links and sanitized output.
- Make save state, conflict state, and another-user editing indicators visible but unobtrusive.
- Keep optimistic UI behavior reversible and reconcile it with the server response.
- Avoid requiring drag-and-drop for core operations; keyboard and ordinary controls must provide equivalent actions.

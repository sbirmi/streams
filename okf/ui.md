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

- Different bundles can use the same hierarchy for different purposes, such as recipes (dish → ingredients/steps), todos, or side projects. These should not require special-purpose UI support.

Views should have stable, shareable URLs. A URL may identify a stream directly or encode a topic, ordering, filters, expansion state, and comment-count preference.

## Keyboard-first actions

Keyboard shortcuts should make frequent navigation and edits fast, but the UI must also provide discoverable mouse/pointer controls. Mouse and keyboard should cover the same core actions where practical; reordering may rely more heavily on pointer interaction.

The eventual action set should cover:

- moving between visible streams/comments
- opening and closing a stream
- expanding/collapsing a topic or stream
- creating, editing, and moving an item
- inserting a new item before, after, or beneath a selected item
- moving an existing item before, after, or beneath another item
- adding a comment
- marking an item done/closed
- showing more comments
- jumping to search or a saved view

Insertion and movement should be possible from context actions, inline controls, or a compact add/move affordance. Drag-and-drop may be the fastest mouse path for reordering, but it should have a clear non-drag fallback and must not be the only way to move an item.

Exact keys, discoverability, focus behavior, and customization remain open. Shortcuts must not interfere with normal text entry in Markdown fields.

## Rendering and feedback

- Render Markdown for summaries, descriptions, and comments with safe links and sanitized output.
- Make save state, conflict state, and another-user editing indicators visible but unobtrusive.
- Keep optimistic UI behavior reversible and reconcile it with the server response.
- Keep mouse targets compact but discoverable, including add-before/add-after/add-child and move controls.
- Avoid requiring drag-and-drop for core operations; keyboard and ordinary controls must provide an equivalent path.
- Preserve focus, scroll position, and the selected item after insertion or movement.

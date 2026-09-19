# User interface direction

Status: proposed.

A standalone visual prototype is available in [`prototype/`](../prototype/). It is the place to settle the first-pass layout and interaction feel before expanding the application implementation.

The UI should optimize for fast rendering, low interaction cost, and information density. It should feel like a quick shared workbench, not a large project-management dashboard.

The current prototype direction favors a dense, list-like surface: minimal padding, no unnecessary cards, one compact header/control area, and stream rows that resemble a semantic unordered list. The first UI pass includes recent comments in a horizontally scrollable comment rail beside each stream; this placement has proved useful for understanding the surrounding conversation without opening another view. Add-stream and reordering controls are also deferred while the reading/editing surface is being evaluated.

When set, priority is rendered as the first metadata tag (for example, `#P0`) and color-coded like any other tag. Priority may be empty. The summary has no unrelated trailing labels; update time, owners, priority, tags, and deadline live in the metadata line beneath it. Owners are displayed as a compact comma-separated list and deadlines as `due YYYY-MM-DD`; empty values are omitted.

The hierarchy is not limited to one child level. Rows may be nested to multiple levels, with indentation and the focus indicator shifting together at each depth.

## Current prototype decisions

The first screen under review is intentionally narrow in scope:

```text
[S] streams : Todos                                    [username] [?]
[ search/filter ]          12 open streams · touched today       [Priority v]

[ ] last update  Summary goes here
    owner1, owner2  #P0 #tag1 #tag2
    Description, if it exists
```

- The topmost bar is the **header**. It shows the Stream identity, bundle breadcrumbs/name, and the user/help controls; common prefixes such as `Bundles/` are omitted. The header uses the full available width, keeps its controls top-aligned, lets the identity/bundle name wrap within the left area when needed, and uses a subtle contrasting surface.
- The username field starts blank when no username cookie exists. A non-empty username is retained in a browser cookie for subsequent visits; clearing the field clears the cookie. The value remains display attribution, not authentication.
- The next bar is the **viewbar**. It is a compact three-column surface: a roughly 200px filter column, a flexible left-aligned view-controls column, and a right-aligned statistics column. The statistics column may shrink to two lines, but stays wide enough to show `12 open streams` / `touched today` without dropping to a separate row.
- The header breadcrumbs show the full rooted path, such as `Index / parent / effort1`; the Index/root view keeps the existing bundle name display. The viewbar’s open/total stream counts cover the current rooted subtree and intentionally do not change when the search filter narrows the displayed rows.
- The header and viewbar remain fixed while the stream list scrolls beneath them.
- Stream rows are list-like rather than cards, with minimal padding and no decorative containers.
- The summary has no unrelated trailing labels. Update time, owners, priority, tags, and deadline appear beneath it.
- Priority is the first tag and is styled like a tag with a distinct color.
- Owners and tags use smaller text.
- Markdown-capable fields look like plain rendered text when idle and become text-like editable surfaces only while editing.
- Add-stream controls and reordering controls are deliberately not shown in this prototype.
- Stream IDs are shown as small numeric chips between the status control and summary. Descriptions and comments can refer to another stream with `@Stream:<number>`; the notation renders as a compact reference chip that reflects whether the referenced stream is open or resolved.
- Reference chips are intended to become actionable: from a chip, a user should be able to inspect the referenced stream and apply status actions such as close or reopen, subject to the normal edit/conflict rules.
- The prototype includes a few resolved streams so their muted/checked treatment can be reviewed; closed-item filtering remains out of scope for this pass.
- Resolved stream summaries are crossed out. Their descriptions collapse to one line by default and expand to the normal five-line allowance when the resolved row is selected/focused.
- `j`/`k` navigate the currently visible rows only; collapsed descendants are skipped. Focus indication follows the row indentation at every nesting depth.
- The selected row is highlighted across its full width so keyboard navigation with `j`/`k` is easy to follow.
- Descriptions may occupy up to five rendered lines in the idle list view; editing can expand the text surface as needed.
- Each stream row has a compact pencil affordance at the end of its summary line for opening the stream modal. The modal supports full-width summary and description fields, a compact inline metadata row for comma-separated owners, numeric priority, and an accessible date-only deadline input, followed by a compact Tags row. Tags accept commas or whitespace as separators and preserve the entered order after empty values are removed. Owners and tags have no suggested names; both may be empty. Required fields use a trailing `*` in their visible label while retaining semantic required attributes; the summary is currently the only required field. Create and edit use the same fields.
- The stream modal shows the server-controlled numeric order key as a read-only field. It is informational and cannot be submitted as an edit; insertion and future movement operations determine it automatically.
- Each stream row has a comment rail beside its stream content. The stream content is capped at 52% on wide screens (while sizing to its content when possible), has a 400px minimum, and is separated from the comment rail by a 20px gap. The rail begins 10px below the stream row’s top edge, has a 300px minimum, shows mock comments horizontally, and allows additional comments to be revealed by horizontal scrolling. Long comment bodies are visibly truncated with a multiline ellipsis; the complete text is reserved for the future modal. It has no decorative separator line.
- Horizontal focus can move from stream content into the comment rail with `h`/`l` or the left/right arrows. The focused comment is highlighted and scrolled into view; vertical movement preserves the comment index when possible.
- `Z Enter` or double-clicking a stream opens that stream as the current rooted view; `Z Backspace` returns to its parent or the `Index` root while preserving focus on the most recently selected stream when it still exists in the newly visible subtree. If that stream was deleted or is otherwise unavailable, focus moves to a safe visible fallback.
- In a rooted view, inserting before or after the focused view root is blocked because it would create an invisible sibling outside the view. Adding a root stream from the toolbar is blocked for the same reason; inserting a child remains available.
- The keyboard-help dialog is generated from the complete server-loaded shortcut map, so configured aliases and sequences remain discoverable without a second hardcoded shortcut list.
- The current rooted view can be shared with a permalink. The URL uses `root=<stream-id>` for a rooted stream, `view=priority|recent|manual|stale` for the selected view, and `focus=stream:<stream-id>` or `focus=comment:<comment-id>` for the focused target. The index root is represented by omitting `root`.
- The URL carries shareable navigation state only. Personal presentation state such as expansion/collapse, local focus restoration, and comment-rail position is persisted client-side per bundle/root context, independently of sort mode, with explicit URL parameters taking precedence. Restoring a focused stream or comment expands only the ancestor chain required to make it visible.
- A visible Copy link action copies the canonical current rooted-view URL. Browser history updates preserve the URL as navigation state without requiring a full page reload.
- A future multi-key command indicator should float across the lower edge of the fixed viewbar, half over the viewbar and half over the list. It should not reserve layout space or move rows, and should disappear when the command completes or is cancelled.

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

### Manual-order view

The View selector offers `Priority`, `Recently touched`, `Manual order`, and `Stale`. Manual order preserves each sibling list’s stored `order_key` sequence, so inserting an item before or after an existing item keeps that placement visible in the hierarchy.

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

Keyboard shortcuts should make frequent navigation and edits fast, but the UI must also provide discoverable mouse/pointer controls. Mouse and keyboard should cover the same core actions where practical; reordering may rely more heavily on pointer interaction. The current shortcut proposal and focus model live in [`keyboard-navigation.md`](keyboard-navigation.md).

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
- For keyboard insertion, render and scroll the insertion placeholder before opening the stream editor modal. Child insertion must show its placeholder even when the focused parent is currently collapsed.
- Deletion is a confirmed action: `d` shows a pending command state and only `d s` or `d c` opens the appropriate confirmation modal. `d c` acts only on the exact comment under focus (`commentIndex`), never implicitly on the newest comment, and is a no-op when stream content has focus. `d s` acts on the containing/focused stream even when the comment rail has focus. The modal explains that deleting a stream promotes its direct children to root-level streams and removes its comments. A stale delete leaves the modal open with a conflict message.
- Each stream row exposes an accessible delete button on hover, selection, or keyboard focus. It opens the same confirmation modal as `d s`, so pointer users have an equivalent stream-deletion path.
- Each comment card exposes an accessible edit button on hover, selection, or keyboard focus. It opens the comment modal in edit mode with the existing body; saving uses the comment revision and preserves comment focus after refresh.

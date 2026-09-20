# Keyboard navigation and shortcuts

Status: proposed. This document is the working home for keyboard navigation, focus behavior, and shortcut decisions. Exact bindings remain subject to prototype review.

## Focus model

The primary view has two focus domains within each visible stream row:

1. **Stream content** — summary, metadata, and description. Initial focus enters here.
2. **Comment rail** — the most recent visible comment followed by older comments from left to right.

Horizontal navigation moves within the current row:

- Right moves from stream content to the most recent comment, then to the next older comment.
- Left moves back through comments and then returns to stream content.
- Up/down moves among visible rows while preserving the current column where possible.
- When a target row has fewer comments than the current comment position, focus should land on its last available comment or stream content.
- Collapsed descendants are not navigation targets.
- Focus must remain visible after movement, including horizontal scrolling of the comment rail.

Arrow keys are supported alongside vi-style keys. The recommended vi-style set is `h`/`j`/`k`/`l` for left/down/up/right. `;` may be considered as an alternate right key if `l` proves awkward, but having one canonical right key is preferable.

When moving vertically, preserve the current comment index where possible. If the destination stream has fewer comments, focus its last available comment, then its stream content if it has no comments.

## Proposed navigation keys

| Key | Action | Notes |
| --- | --- | --- |
| `h` / Left | Move left | Previous comment, then stream content. |
| `l` / Right | Move right | Stream content, then next older comment. |
| `j` / Down | Move to the next visible row | Keeps the current focus column when possible. |
| `k` / Up | Move to the previous visible row | Keeps the current focus column when possible. |
| `(` | Previous item at the same hierarchy level | May jump past a parent stream to its aunt’s first descendant; if no same-level target exists, focus the aunt. |
| `)` | Next item at the same hierarchy level | May jump past a parent stream to its aunt’s first descendant; if no same-level target exists, focus the aunt. |
| `Home` / `g g` | First visible item | `g g` is a possible vi-style alias. |
| `End` / `G` | Last visible item | `G` is a possible vi-style alias. |
| `PageUp` / `PageDown` | Move by a viewport | Preserve the focus column. |
| `/` | Focus search/filter | Do not intercept while editing text. |
| `Z Enter` | Re-root the view at the focused stream | The focused stream becomes the current view root. |
| `Z Backspace` | Pop the current view root | Returns to the parent stream or `Index`, preserving the most recently selected stream when it still exists in the newly visible subtree; otherwise focuses a safe visible fallback. No-op at `Index`. |
| `?` | Open shortcut help | Existing prototype behavior. |
| `Escape` | Leave modal or restore row focus | Modal focus is restored to the object that opened it. |

## Editing and destructive actions

The object under focus determines which modal opens:

- Stream content opens the stream-content modal.
- A comment opens the comment modal. In add mode, the modal creates a new comment; in edit mode, it loads the selected comment and saves through the revision-checked comment update endpoint.

| Key | Action | Notes |
| --- | --- | --- |
| `e` | Edit the focused stream or comment | Opens the stream editor or the selected comment editor. |
| `d s` | Delete the focused stream | Opens a stream-delete confirmation modal; acts on the containing stream even when the comment rail has focus; never delete on a single `d`. |
| `d c` | Delete the focused comment | Opens a comment-delete confirmation modal for the exact comment at `commentIndex`; it never implicitly targets the newest comment and is a no-op when stream content has focus; never delete on a single `d`. |
| `a` | Add a comment to the focused stream | Opens the comment modal in create mode. |

The modal must trap focus, support `Escape`, and return focus to the original stream/comment after close or save. A failed or stale save must keep the modal open with a clear conflict state visible. Comment cards expose an accessible pointer edit button using the same edit modal.

The stream row’s accessible delete button is the pointer equivalent of `d s` and uses the same confirmation and conflict handling.

## Creating and moving streams

The product uses explicit two-key commands for inserting a stream above, below, or beneath the focused stream:

| Key | Action | Notes |
| --- | --- | --- |
| `ip` | Add a stream before the focused stream | `i` alone only shows pending-command feedback. |
| `in` | Add a stream after/below the focused stream at the same level | |
| `ic` | Add a child stream below the focused stream | Creates the next indented item. |
Moving an existing stream uses a general move mode instead of a separate shortcut for every relative case:

| Key | Action | Notes |
| --- | --- | --- |
| `m` | Pick up the focused stream | Starts move mode; navigation chooses the destination. |
| `v` | Start/extend or finish a contiguous sibling selection | Press `v` again to stop extending; the highlighted block remains selected. Press `m` to pick it up, then navigate to the target. |
| `p` | Place before the focused target | Completes move mode. |
| `n` | Place after the focused target | Completes move mode. |
| `c` | Place as the focused target’s first child | Completes move mode. |
| `u` | Promote one level | Places the selection after its current parent; unavailable for root streams or invisible rooted-view mutations. |

Move mode shows a persistent command hint, for example:

```text
[m] moving 1 stream → target: Project X · [p] before · [n] after · [c] child · [u] promote · [Esc] cancel
```

The generic command HUD describes every valid next key with its action, rather than showing only bare key names. Prefixes use the same format, for example:

```text
[z] fold · [o] open one level · [O] open descendants · [c] close one level · [C] close descendants · [a] toggle hierarchy
```

The previous `>>`/`<<` shortcuts are retired in favor of move mode. Pointer move controls should use the same destinations and server operation.

The `ip`/`in`/`ic` family makes the insertion destination explicit and prevents a lone `i` from mutating data. Each sequence shows its pending state and cancels on `Escape`.

When the current view has no focused stream, `ic` is a no-op because there is no parent for a child insertion. In a rooted view, `ip` and `in` are blocked when the focused stream is the view root because their siblings would be outside the visible subtree. `ic` remains allowed. The toolbar root-add action is also blocked in a rooted view.

Moving and inserting must have mouse/pointer equivalents and must preserve selection, focus, and scroll position.

When `ip`, `in`, or `ic` starts insertion, the UI renders and scrolls the insertion placeholder into view before opening the stream editor modal. The placeholder remains visible behind the modal and identifies the exact destination; `ic` must expose that placeholder even if the focused parent was collapsed.

Double-clicking a stream row is the pointer equivalent of `Z Enter`. Re-rooting changes the visible subtree but does not change stream hierarchy or folding state.

## Folding and expanding

The current preferred fold vocabulary is a `z` prefix:

- `zo`: open one level.
- `zO`: recursively open all descendants.
- `zc`: close one level.
- `zC`: recursively close all descendants.
- `za`: toggle the focused hierarchy.

The previous repeated-key idea (`o`, `oo`, `ooo`, `c`, `cc`, `ccc`) is retired in favor of this prefix form. It avoids ambiguity with insertion and makes “open all”/“close all” easier to explain.

Future level-wide operations could use a level prefix, such as `l o` / `l c`, to apply opening or closing to sibling streams at the current level. This is intentionally not settled.

## Command-sequence feedback

Multi-key commands should show a small transient command HUD near the focused row or in a stable viewbar position. The HUD shows the keys already entered, the command meaning, and the valid next keys.

For example, after starting a hypothetical level command:

```text
[l] level operation  ... z/r/l
```

After pressing `z`:

```text
[lz] level fold      ... o/O/c/C/a
```

The HUD should:

- appear as soon as a command prefix is recognized;
- replace the available-next-key hint after each key;
- disappear after the command completes;
- cancel the pending sequence on `Escape`;
- optionally support Backspace to remove the last prefix key;
- time out an abandoned prefix after a short, visible interval.

The same feedback model applies to `ip`, `in`, `ic`, `ds`, and `dc`, with the next valid choices shown after the prefix. A pending command must not mutate data.

Modifier-only browser key events such as `Shift`, `Control`, `Alt`, `Meta`, and `CapsLock` are ignored while matching a pending sequence. This allows shifted bindings such as `zO` to be entered as `z`, `Shift`, `o` without treating the browser’s intermediate `Shift` event as an invalid command token. The final `event.key` remains the configured key (`O` in this example), and modifier-only keys are not commands themselves.

The automated suite does not synthesize browser `keydown` ordering, so shifted-sequence behavior should also be smoke-tested in a browser.

After confirmation, deletion sends the focused object’s revision to the API. On success, the UI refreshes the list and restores focus to the nearest surviving stream; for a comment, focus remains on its stream. On a stale response, the confirmation modal remains open and explains that the current item must be reviewed before retrying.

The `Z` prefix uses the same feedback model and accepts `Enter` or `Backspace` as its second key. A pending `Z` must not change the view until the second key arrives.

## Shortcut configuration

The complete shortcut map lives in [`config/shortcuts.yaml`](../config/shortcuts.yaml) rather than being customized through the UI. Configuration changes take effect after an application restart. Each action is declared exactly once as `action: binding` or `action: [binding, binding]`; compact sequences such as `ds` and `ip` are key-event sequences, while named keys use spaces (`Z Enter`, `ArrowDown`). The server loads this small flat format without a YAML dependency and exposes the resulting action-to-list map at `/api/shortcuts`. The browser derives both command prefixes and dispatch from that response, so a binding absent from the file is not accepted. Missing, unreadable, incomplete, duplicate, or malformed files fail application startup rather than silently restoring hardcoded defaults.

`Escape` is configured for cancelling a pending command. Escape handling inside native modal dialogs remains the browser/dialog platform behavior; the configuration does not replace modal focus trapping or closing semantics.

## Open questions

- Should right/left focus the comment card as a whole, or a specific link/control inside it?
- Should `(` and `)` use the aunt fallback exactly as described, or stop when no same-depth target exists?
- Should command HUD placement follow the focused row, or remain fixed in the viewbar?

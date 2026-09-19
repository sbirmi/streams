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
| `Z Backspace` | Pop the current view root | Returns to the parent stream or `Index`; no-op at `Index`. |
| `?` | Open shortcut help | Existing prototype behavior. |
| `Escape` | Leave modal or restore row focus | Modal focus is restored to the object that opened it. |

## Editing and destructive actions

The object under focus determines which modal opens:

- Stream content opens the stream-content modal.
- A comment opens the comment modal.

| Key | Action | Notes |
| --- | --- | --- |
| `e` | Edit the focused stream or comment | Opens the appropriate modal. |
| `d s` | Delete the focused stream | Opens a stream-delete confirmation modal; never delete on a single `d`. |
| `d c` | Delete the focused comment | Opens a comment-delete confirmation modal; never delete on a single `d`. |
| `a` | Add a comment to the focused stream | Opens the comment modal in create mode. |

The modal must trap focus, support `Escape`, and return focus to the original stream/comment after close or save. A failed or stale save must return focus with the conflict state visible.

## Creating and moving streams

The product needs commands for inserting a stream above, below, or beneath the focused stream. A possible first vocabulary is:

| Key | Action | Notes |
| --- | --- | --- |
| `i` | Add a stream before the focused stream | “Insert” before. |
| `o` | Add a stream after/below the focused stream at the same level | Folding uses the separate `z` prefix. |
| `O` | Add a child stream below the focused stream | Creates the next indented item. |
| `> >` | Indent/move the focused stream beneath its previous sibling | The two `>` keys must arrive as a quick sequence. |
| `< <` | Outdent/move the focused stream to its parent’s level | The two `<` keys must arrive as a quick sequence. |

`i`/`o`/`O` mirror the familiar insert-before, insert-after, and insert-child distinction. `>>`/`<<` avoid taking over Tab and Shift-Tab, which remain available for browser and accessibility focus movement. They also fit the visual language of moving a stream right or left. Each sequence should show its pending state and cancel on `Escape`.

When the current view has no focused stream, `O` is a no-op because there is no parent for a child insertion. `i` and `o` may still create a root-level stream from the empty `Index` view.

Moving and inserting must have mouse/pointer equivalents and must preserve selection, focus, and scroll position.

When `i`, `o`, or `O` starts insertion, the UI renders and scrolls the insertion placeholder into view before opening the stream editor modal. The placeholder remains visible behind the modal and identifies the exact destination; `O` must expose that placeholder even if the focused parent was collapsed.

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

The same feedback model applies to `>>`, `<<`, `ds`, and `dc`, with the next valid choices shown after the prefix. A pending command must not mutate data.

The `Z` prefix uses the same feedback model and accepts `Enter` or `Backspace` as its second key. A pending `Z` must not change the view until the second key arrives.

## Shortcut configuration

The default shortcut map lives in [`config/shortcuts.yaml`](../config/shortcuts.yaml) rather than being customized through the UI. Configuration changes take effect after an application restart. The initial implementation uses a small flat YAML map for `insert_before`, `insert_after`, and `insert_child`; missing or invalid files fall back to the documented defaults and emit a warning.

## Open questions

- Should right/left focus the comment card as a whole, or a specific link/control inside it?
- Should the shortcut configuration grow beyond the initial flat insertion map, and if so should it adopt a full YAML parser/schema?
- Should invalid shortcut configuration fail startup, warn and use defaults, or ignore only invalid entries?
- Should `(` and `)` use the aunt fallback exactly as described, or stop when no same-depth target exists?
- Should command HUD placement follow the focused row, or remain fixed in the viewbar?

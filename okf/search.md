# Search

Status: proposed product behavior and source of truth for search syntax and result presentation.

Search is a single query field for finding streams and their comments. It works within the current destination and rooted scope. The query is retained in the URL so a search can be bookmarked and shared.

## Query grammar

The initial language is intentionally small:

```text
query      := expression*
expression := ["-"] (field | phrase | word)
field      := name ":" value
phrase     := '"' characters '"'
word       := non-whitespace text
```

Whitespace separates expressions. A quoted phrase keeps its spaces. Field names and values are case-insensitive unless a future field explicitly documents otherwise. Unknown `name:value` expressions are treated as ordinary keyword expressions in the initial client-side implementation; adding validation later requires updating this document.

## Matching semantics

- Every positive expression must match. Spaces therefore mean implicit **AND**.
- A leading `-` negates one expression. A negated expression must not match.
- Bare words and phrases search stream summaries, descriptions, comments, owners, and tags. Matching is case-insensitive. A phrase must occur contiguously in one searchable text value; it does not span fields.
- Positive and negative expressions can be combined freely. `foo lorem -bar` requires `foo` and `lorem` and excludes any item matching `bar`.
- The first version does not define `OR`, parentheses, wildcards, regular expressions, fuzzy matching, or arbitrary field names. They may be added later only by updating this document.

The result unit is a stream. A stream matches when its own searchable fields match, or when one of its comments matches. A comment match should identify the matching comment and show a short excerpt when the UI can do so.

## Supported fields

The initial field filters are:

| Filter | Meaning |
| --- | --- |
| `status:open` | Stream is open. |
| `status:resolved` | Stream is resolved. |
| `status:no_action` | Stream is marked “No action needed”. |
| `status:any` | Include streams of every status. |
| `priority:3` | Stream priority is exactly `3`. |
| `priority:none` | Stream has no priority. |
| `tag:X` | Stream has the exact tag `X`. |
| `owner:X` | Stream has the owner value `X`. |
| `id:123` | Stream ID is exactly `123`. |

Field values are exact values, except where a field’s value syntax says otherwise. In particular, `tag:foo` does not match `foobar`, and `priority:3` does not match another priority. Tags and owners use the same normalized, trimmed values stored by the application.

A leading `-` negates a field filter: `-priority:3`, `-tag:blocked`, or `-status:resolved`. Negating `status:any` is not useful and should be rejected as invalid query syntax.

Priority values are the stored numeric priority or `none`; lower numeric priorities remain higher priority in the normal view. Status values are exactly `open`, `resolved`, and `no_action`.

## Default status scope

Without a status filter, search uses the current view’s normal status scope. In the default priority view this means open streams first, with closed streams governed by that view’s existing closed-item setting. Search must not silently change the view’s status policy merely because a query is present.

Use `status:any` when the user explicitly wants all statuses, or use a specific status filter to find one terminal state. `status:resolved foo` searches resolved streams containing `foo`.

## Rooted scope and result presentation

Search is constrained to the current root:

- At the Index root, candidates are all streams in the bundle.
- In a rooted stream view, candidates are the rooted stream and every descendant, at any depth.
- A stream outside the current rooted subtree must not appear solely because a matching comment or child exists elsewhere.

Search results are displayed as a flat result set within the active view, while retaining enough hierarchy context to understand each result. Each result shows the stream meeting the query and its relative breadcrumb/path from the current root. A matching comment should be indicated near the result.

When a match is found at depth N, expand only the minimum ancestor chain needed to make that matching stream visible: expand each ancestor between the current root and the matching stream, and expand the matching stream only as needed to show the matched content. Do not expand unrelated siblings, cousins, or descendants. If multiple matches share ancestors, expand the union of their required paths, still leaving unrelated branches collapsed.

This minimum-expansion rule applies whether the match is in the stream itself or in one of its comments. It also applies when a search URL is opened directly. Expansion is presentation state; the query and rooted destination are shareable URL state.

## URL and sharing

The current search query is encoded as `q` in the canonical URL. It is combined with the existing `root`, `view`, and typed `focus` parameters. For example:

```text
/?q=priority%3Anone%20tag%3Afrontend%20foo&view=priority
```

The Index root is represented by omitting `root`. A rooted search might look like:

```text
/?root=42&q=foo%20-bar&view=recent
```

The URL must preserve the query text sufficiently for the user to edit and reshare it. Client-local expansion, focus restoration, scroll position, and comment-rail position remain local presentation state and are not encoded into the search query.

## Examples

```text
foo bar
```

Find streams matching both `foo` and `bar`.

```text
foo lorem -bar
```

Require `foo` and `lorem`, while excluding streams matching `bar`.

```text
priority:none tag:frontend tag:urgent
```

Find unprioritized streams with both exact tags.

```text
status:resolved -tag:wontfix
```

Find resolved streams that do not have the exact `wontfix` tag.

```text
"release candidate" owner:alice -priority:3
```

Find the exact phrase for Alice, excluding priority 3.

```text
status:any foo
```

Find `foo` across open, resolved, and no-action streams, subject to the current root.

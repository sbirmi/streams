# External references and integrations

Status: proposed.

The application may recognize references to tools hosted elsewhere—such as Jira, Bugzilla, Google Docs, spreadsheets, or chat messages—and render them as links. The first implementation should prefer links over fetched previews.

Descriptions and comments are the reference-enabled Markdown bodies. Summaries are plain text and are not passed through Markdown or reference substitution.

## Configuration direction

Reference recognition should be driven by reviewed, deployment-controlled declarative configuration. A rule may define:

- a name and identifier pattern, for example `Foo([0-9]+)`;
- the canonical URL template, for example `https://bugs.example.test/show_bug.cgi?id={1}`;
- display text and optional rendering behavior;
- whether matching is case-sensitive.

For example, a configured `Foo12345` match could render as a link to `https://jira.example/task/12345`. Built-in rules cover `Stream:<ID>` and a comment reference notation that links directly to the referenced object. The exact comment syntax and configuration schema remain open.

The rendering pipeline is:

```text
raw Markdown -> Markdown HTML -> sanitize -> reference substitution in text nodes -> validate/sanitize links
```

Substitution does not rewrite existing links, inline code, or fenced code blocks. The original source text is always preserved for editing, history, export, and conflict handling.

## Safety and behavior

- Configuration is deployment-controlled, not editable by ordinary users.
- Generated links must be validated and restricted to configured schemes/hosts as appropriate.
- Rules are declarative only: they may construct a validated URL and label, but may not execute code or inject arbitrary HTML, CSS, or JavaScript.
- Matching is bounded and deterministic. Rule ordering and collision behavior must be documented before implementation.
- Reference matching should preserve the original text and remain usable when the external service is unavailable.
- External pages should normally open as links; fetching remote content or embedding previews is a separate decision with additional security and latency implications.
- Rules should be deterministic, bounded, and compiled/validated at startup where possible.

## Plugin-rendered styles

If a plugin or configured integration adds a special rendering, it may declare an optional style name and the CSS definitions/classes needed for that rendering. Plugin styles should be:

- scoped under a plugin-specific root class or attribute;
- namespaced to avoid changing the application’s base UI;
- reviewed and bundled as static assets rather than fetched at runtime;
- subject to the same supply-chain and content-security review as plugin code.

The plugin metadata should make the rendering name, required styles, and any required markup/classes explicit. A plugin should not inject arbitrary unscoped CSS into the whole application.

# External references and integrations

Status: proposed.

The application may recognize references to tools hosted elsewhere—such as Jira, Bugzilla, Google Docs, spreadsheets, or chat messages—and render them as links or compact previews.

## Configuration direction

Reference recognition should be driven by a reviewed YAML configuration file. A rule may define:

- a name and identifier pattern, for example `BUG([0-9]+)`;
- the canonical URL template, for example `https://bugs.example.test/show_bug.cgi?id={1}`;
- display text and optional rendering behavior;
- whether matching is case-sensitive.

For example, a configured `BUG123` match could render as a link to the configured bug tracker URL. The exact schema is intentionally not fixed yet.

## Safety and behavior

- Configuration is deployment-controlled, not editable by ordinary users.
- Generated links must be validated and restricted to configured schemes/hosts as appropriate.
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

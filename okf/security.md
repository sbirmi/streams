# Security and supply-chain baseline

## Trust boundary

The initial deployment assumes the service is reachable only from a secure, controlled network. URL reachability currently implies read/write access. This does not remove the need for safe input handling, secure transport, backups, or dependency review.

The service must not be described or configured as public-internet safe without adding authentication, authorization, abuse controls, and a threat-model update.

## Baseline controls

- Validate and bound all request fields, including note and comment sizes.
- Render user content safely; prevent stored and reflected script injection.
- Treat Markdown as untrusted input and sanitize rendered HTML; do not allow arbitrary raw HTML or unsafe URL schemes by default.
- Treat configurable external-reference rules as trusted application configuration, not user-authored content; validate generated URLs and avoid shell/template execution.
- Scope plugin CSS and markup so a plugin cannot unexpectedly restyle or interfere with the core interface; review plugin assets as code/dependencies.
- Use parameterized datastore operations and avoid shell evaluation of user input.
- Protect state-changing requests against cross-site request forgery if browser cookies are used.
- Use HTTPS or a trusted internal TLS boundary in deployment.
- Keep secrets out of source control and logs.
- Treat the user-provided username as untrusted display data; escape it when rendered and never use it for authentication, authorization, or security decisions.
- Log operational events without logging unnecessary note contents or secrets.
- Define backup access and retention; backups contain user-authored data.
- Run with least filesystem and network privileges available in the chosen deployment.

## Supply-chain posture

- Keep the dependency graph small.
- Pin versions using the ecosystem’s lockfile and review lockfile changes.
- Prefer well-maintained, broadly used dependencies with clear licenses.
- Build from a reproducible or at least documented environment.
- Review container/base-image updates and scan dependencies/images where tooling exists.
- Do not add a package merely to avoid a small amount of local code.
- Document any exception or new trust-bearing dependency in `decisions.md`.

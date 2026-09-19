# Deployment guide

Status: initial outline; commands will be filled in when the implementation and packaging are selected.

## Deployment assumptions

- Run inside the trusted network.
- Put the app behind an internal reverse proxy or equivalent gateway where practical.
- Persist the datastore on durable storage outside the application process/container lifecycle.
- Restrict datastore and management access to the operators who need it.
- Keep a tested backup before upgrades.
- If SQLite WAL mode is used, back up the database together with its active `-wal`/`-shm` state or use a SQLite-aware backup procedure; do not copy only the main database file during active use.

## Required operational capabilities

The eventual deployment must document:

- Python/runtime version and virtualenv creation/activation
- configuration and environment variables
- listening address and proxy/TLS expectations
- persistent data location
- health/readiness check
- startup, shutdown, and upgrade procedure
- database migration execution and failure handling
- backup and restore procedure
- log locations and useful diagnostics
- rollback procedure
- dependency and image update process

## Run the tests

From the repository root, run:

```sh
./scripts/test
```

The script creates or reuses `.venv`, installs the pinned dependencies from `requirements.lock`, and runs the test suite. A successful run ends with `OK`.

## Start the service locally

From the repository root, run:

```sh
./scripts/run
```

The script creates or reuses `.venv`, installs the pinned dependencies, runs database migrations on startup, and starts Flask at <http://127.0.0.1:5000/>. Stop it with `Ctrl-C`.

The default database is `data/stream.sqlite3`. For a different local address or database path, set environment variables before starting:

```sh
STREAM_HOST=0.0.0.0 STREAM_PORT=5000 STREAM_DATABASE_PATH=data/stream.sqlite3 ./scripts/run
```

Use `GET /healthz` for a basic health check. Do not bind to a public interface without first revisiting the trusted-network security model.

The complete shortcut map is in `config/shortcuts.yaml`. Set `STREAM_SHORTCUTS_PATH` to use another file; the strict action-to-bindings configuration is loaded at service startup. Every implemented keyboard action must be present, and a missing, malformed, duplicate, or incomplete file prevents startup so the browser cannot silently fall back to hardcoded bindings.

## Backup principle

Back up the datastore as an application-consistent snapshot or through its supported dump mechanism. Test restoring into an isolated instance before relying on a backup. Record the last verified restore in the operational notes or deployment history.

## Exposure warning

Do not bind the service to a public interface or publish it through an internet-facing proxy without revisiting the trust model and implementing authentication and authorization.

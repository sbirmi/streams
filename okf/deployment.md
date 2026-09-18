# Deployment guide

Status: initial outline; commands will be filled in when the implementation and packaging are selected.

## Deployment assumptions

- Run inside the trusted network.
- Put the app behind an internal reverse proxy or equivalent gateway where practical.
- Persist the datastore on durable storage outside the application process/container lifecycle.
- Restrict datastore and management access to the operators who need it.
- Keep a tested backup before upgrades.

## Required operational capabilities

The eventual deployment must document:

- configuration and environment variables
- listening address and proxy/TLS expectations
- persistent data location
- health/readiness check
- startup, shutdown, and upgrade procedure
- backup and restore procedure
- log locations and useful diagnostics
- rollback procedure
- dependency and image update process

## Backup principle

Back up the datastore as an application-consistent snapshot or through its supported dump mechanism. Test restoring into an isolated instance before relying on a backup. Record the last verified restore in the operational notes or deployment history.

## Exposure warning

Do not bind the service to a public interface or publish it through an internet-facing proxy without revisiting the trust model and implementing authentication and authorization.


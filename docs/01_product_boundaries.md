# Product Boundary Decision

## Status

Accepted for the backend rewrite foundation.

## Context

Listening Journal is being rewritten from Phoenix to Django while retaining the
existing Svelte frontend. The Django repository was derived from SODA Starter,
which includes more infrastructure than the application currently exercises.

The Django application starts with a fresh database. No Phoenix SQL migration,
production-data import, or cross-database identifier preservation is in scope.
The Phoenix implementation may inform product behavior and frontend integration,
but its storage schema is not a compatibility target.

Removing every unused subsystem immediately would reduce the initial codebase,
but tags, catalogue images, and organization data exports are plausible product
features. They are already implemented and tested in the starter. Retaining
them avoids speculative deletion followed by reimplementation without forcing
the frontend to expose them before they are ready.

The rewrite will use UUID identifiers and a PostgreSQL-backed task queue. These
choices affect the retained generic relations and export workflow and must be
handled before clean initial migrations are generated.

## Decision

### Retained foundations

The rewrite keeps:

- accounts and hardened first-party authentication;
- organizations and membership roles;
- contacts and avatars;
- PostgreSQL;
- S3/R2-compatible storage;
- tags;
- images, polymorphic image relations, image sharing, and bulk image operations;
- organization data exports;
- durable idempotency;
- production settings, checks, deployment guidance, and operational tooling.

Retaining a subsystem does not require registering all of its routes. Unused or
incomplete public endpoints may remain disabled until the API-contract and
product work make them intentional.

### Removed or replaced foundations

The rewrite will:

- remove the separate browser-authentication API unless the Svelte integration
  proves that it is required;
- replace `NinjaExtraAPI` with Django Ninja's `NinjaAPI` because no Ninja Extra
  controller or dependency-injection features are in use;
- replace Celery, Beat, Redis broker state, and Redis caching with
  Procrastinate and PostgreSQL-backed alternatives;
- replace cache-only security throttles with durable PostgreSQL-backed controls
  for login, registration, verification, password reset, and similar sensitive
  operations.

### Terminology

New Python and domain code uses **Organization** consistently. Compatibility
routes may retain `/workspaces` temporarily where doing so materially reduces
frontend migration risk. Any temporary terminology mismatch must be documented
in the API-contract work and removed deliberately rather than allowed to spread
through new domain code.

### API compatibility

The Phoenix OpenAPI document and the frontend's generated schema are behavioral
references. The initial Django API should preserve frontend-visible conventions
where practical, including:

- `/api/...` routes;
- top-level `data` envelopes;
- the existing pagination shape;
- structured `{errors: [{code, message, field}]}` responses;
- UUID identifiers;
- workspace/organization and creator identifiers;
- refresh-token rotation;
- current-workspace behavior.

Differences from the Phoenix contract must be intentional and recorded.

This API policy exists to support the retained Svelte frontend. It does not
imply database compatibility with Phoenix or require importing Phoenix data.

### Foundational account and organization semantics

- User preferences are named `theme` and `locale`.
- Theme values are `system`, `light`, and `dark`.
- New users initially prefer their automatically created personal organization.
- Python code names the relation `current_organization`; the transitional API
  field is `current_workspace_id` while the frontend still uses that term.
- Organization kinds are `personal` and `shared`.
- Membership roles are `owner`, `admin`, and `member`.
- Shared organizations must always retain an active owner; PostgreSQL enforces
  this with deferred constraint triggers in addition to service-layer checks.
- Organization settings remain a JSON object for future organization-scoped
  preferences.

## UUID consequences

All externally visible resources will use UUID primary keys. Before generating
the derived project's clean initial migrations:

- convert users, organizations, contacts, tags, images, export jobs, and other
  externally addressable models to UUID primary keys;
- change `TaggedItem.object_id` from `PositiveIntegerField` to `UUIDField`;
- change `PolymorphicImageRelation.object_id` from `PositiveIntegerField` to
  `UUIDField`;
- update polymorphic resolver function annotations, schemas, route parameters,
  indexes, constraints, serializers, and tests;
- keep explicit allowlists for taggable and imageable model types;
- decide separately whether internal join rows need UUID primary keys or can
  retain ordinary database-generated identifiers.

Using generic relations means the database cannot enforce a foreign key from a
tag or image relation to its target object. Application allowlists,
organization-scope checks, deletion behavior, and integration tests therefore
remain mandatory.

## Export consequences

Organization exports remain part of the product foundation and must be migrated
from Celery to Procrastinate. The migration must preserve:

- durable export job states;
- authorized enqueue, list, detail, and retry behavior;
- safe redelivery and duplicate execution;
- deterministic object replacement;
- heartbeat and stale-job recovery;
- cleanup of expired archives;
- cleanup of uploaded objects when the ready-state transition fails;
- short-lived authenticated download URLs.

The export archive currently covers only the retained starter-era domains. Its
schema and tests must expand as catalogue, journal, list, curator, and other
user data is ported. Until that work is complete, the endpoint should be
disabled or clearly labeled experimental.

The feature may support data-portability and privacy obligations, but the
project must not claim that the export alone makes the application GDPR
compliant.

## Image consequences

Images are retained without speculative simplification. Artists, works,
releases, lists, contacts, and organizations may require images or cover art.
The complete image API will be reassessed when catalogue-image requirements are
known.

Before exposing image sharing publicly, confirm that its private-storage,
authorization, expiry, revocation, and cache behavior matches the Listening
Journal product rather than merely preserving starter behavior.

## Consequences

This decision keeps more tested code in the initial foundation and makes the
Celery-to-Procrastinate migration larger, principally because organization
exports remain asynchronous. It also makes UUID conversion broader because two
generic relation systems must be updated.

In return, the rewrite avoids deleting plausible product capabilities before
their requirements are understood, retains a substantial background-workflow
example, and postpones image simplification until it can be driven by real
catalogue use cases.

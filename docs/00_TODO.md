# Listening Journal — Backend Migration TODO

## 1. Preserve the reference implementation ✅

**Status:** Complete.

Before changing behavior:

- Rename the current Elixir directory to `backend-phoenix`.
- Tag or commit its current working state.
- Preserve its OpenAPI schema.
- Preserve a representative seed/catalogue export.
- [x] Start Django with a fresh database; do not build a Phoenix SQL/data import path.

> The Phoenix backend remains the behavioral reference, not a code template.

---

## 2. Rename the Django project ✅

**Status:** Complete in `chore: adopt SODA starter for Listening Journal`.

Use the starter's renaming script:

```bash
uv run python scripts/rename_project.py listening_journal \
  --distribution listening-journal-api \
  --display-name "Listening Journal"
```

Then remove starter-only material from the derived product:

- `scripts/rename_project.py` and its tests
- `docs/public-release-checklist.md`
- Starter-specific adoption and branding documentation
- SODA-specific README language

Commit this separately as something like:

```
chore: adopt SODA starter for Listening Journal
```

---

## 3. Write down the product boundaries ✅

**Status:** Complete in `docs/01_product_boundaries.md`; commit pending.

Before deleting code, create a short architecture decision document covering what stays.

| Starter subsystem                          | Decision                                            |
| ------------------------------------------ | --------------------------------------------------- |
| Accounts and hardened authentication       | Keep                                                |
| Organizations and membership roles         | Keep                                                |
| Contacts and avatars                       | Keep                                                |
| PostgreSQL                                 | Keep                                                |
| S3/R2 storage                              | Keep                                                |
| Images and image sharing                   | Keep intact until catalogue-image design            |
| Tags                                       | Keep; convert polymorphic identifiers to UUID       |
| Organization exports                       | Keep; migrate background work to Procrastinate      |
| Browser-specific auth API                  | Remove unless the Svelte architecture needs it      |
| Celery, Beat, Redis                        | Replace with Procrastinate                          |
| Ninja Extra                                | Remove; use plain NinjaAPI                          |
| Idempotency                                | Keep                                                |
| Production settings and checks             | Keep and adapt                                      |

> The existing SvelteKit server already receives JSON access/refresh tokens and stores them in its own HttpOnly cookies. That means the starter's separate browser-cookie authentication contract is probably redundant.

Also decide terminology. Use **Organization** consistently in new Python/domain code because the domain documents already describe the app as organization-centric. The API can temporarily retain `/workspaces` if minimizing frontend churn is more important.

---

## 4. Fix identifiers before generating a real database ✅

**Status:** Complete. The foundational models and clean migrations are settled.

> **This is the most important early change.**

The starter currently uses integer primary keys for users, organizations, contacts, and images, while Listening Journal exposes UUIDs. Its polymorphic image relation also uses `PositiveIntegerField`.

Before relying on the starter migrations:

- [x] Give every externally visible model a UUID primary key.
- [x] Change generic tag and image relation targets to UUIDs.
- [x] Keep ordinary database-generated identifiers for internal association rows.
- [x] Use `theme`, `locale`, and 120-character profile names while retaining useful starter profile fields.
- [x] Add the current-organization preference, exposed temporarily as `current_workspace_id`.
- [x] Use `personal` and `shared` organization kinds with `owner`, `admin`, and `member` roles.
- [x] Retain timezone-aware timestamps and explicit cascade/SET NULL deletion behavior.

Because this is an undeployed derived project, don't create a chain of migrations converting the starter schema. Modify the models, remove the derived project's starter migrations, and generate clean initial migrations once the foundational models settle.

The clean initial migrations have been regenerated. PostgreSQL setup now includes:

- [x] `pg_trgm`
- [x] `unaccent`

---

## 5. Remove unused product features ✅

**Status:** Complete. The redundant browser-cookie authentication API was
removed as a vertical slice; no retained product subsystem was removed.

Delete features as complete vertical slices — models, routes, services, migrations, tests, settings, and documentation together.

Remove only the starter surfaces that are not part of the intended product:

1. [x] Browser-auth routes and their schemas, settings, tests, and documentation
2. [x] No other route or sample behavior is currently rejected by the product-boundary decision

> Keep tags, images, image sharing, bulk image operations, and organization exports for now. Reassess the image API when catalogue-image requirements are concrete rather than removing tested capabilities speculatively.

---

## 6. Replace the background-job subsystem

**Replace:**

- Email delivery
- Expired-token cleanup
- Idempotency-record cleanup
- Abandoned-image cleanup
- Organization export generation
- Export enqueueing and retries
- Export heartbeat and stale-job recovery
- Export retention cleanup

**Then remove:**

- Celery
- `django-celery-beat`
- Redis client/cache packages
- Celery application wiring
- Beat schedules
- Redis/worker/Beat Compose services
- Corresponding CI services
- Celery-specific tests and `.delay()` mocks

**Add:**

- Procrastinate integration and migrations
- A worker service
- Retry policies
- Periodic cleanup schedules
- Task idempotency tests
- Worker health/operational documentation
- Export redelivery, recovery, and deterministic-object tests adapted to Procrastinate

> Don't mechanically wrap Celery-shaped tasks. Define product operations first, with thin Procrastinate entry points invoking those operations.

Organization exports must evolve as catalogue, journal, list, and curator data is ported. Do not describe the export as complete or GDPR-compliant until its coverage and the surrounding operational process have been reviewed. Keep the endpoint disabled or clearly experimental while its payload is incomplete.

Redis also backs Ninja throttling currently. Replace security-sensitive login, registration, verification, and reset throttles with durable PostgreSQL-backed controls. Don't silently switch production throttling to `LocMemCache`, because it is not coordinated across processes.

---

## 7. Establish the API contract

Before porting endpoints, decide how closely Django must match Phoenix.

**Preserve the frontend-visible conventions initially:**

- `/api/...` routes
- Top-level `data`
- Existing pagination structure
- `{errors: [{code, message, field}]}`
- UUID identifiers
- `workspace_id` / `creator_id` exposure
- Refresh-token rotation
- Existing auth route names
- Current-workspace behavior

**The starter currently differs in all of these areas:**

- `/api/v1`
- `{detail: ...}` errors
- Integer IDs
- Organization-slug routing
- Different registration flow
- Token fields named `access` and `refresh` instead of the current payload
- Different profile fields

Use the frontend's committed OpenAPI schema and the Phoenix schema as a migration checklist. Every intentional contract change should be recorded rather than occurring accidentally.

---

## 8. Prove the foundation with one vertical slice

Before creating catalogue models, make the existing Svelte frontend work against Django for:

- Registration and email verification
- Login
- Refresh rotation
- Logout and logout-all
- `/auth/me`
- Current organization/workspace
- Profile updates
- Contacts
- Contact and organization avatars

This exercises nearly every retained starter subsystem:

```
Svelte → Ninja → auth → organization scope → PostgreSQL
                       ↘ Procrastinate email
                       ↘ R2/avatar storage
```

> **Exit criterion:** the Svelte authentication, profile, contacts, and avatar flows pass against Django without the Phoenix server running.

---

## 9. Port the domain incrementally

Only after that baseline is stable:

1. Artists and aliases
2. Works and composers
3. Interpretations and credits
4. Recordings
5. Tunes
6. Releases, credits, and ordered items
7. PostgreSQL search
8. Django admin catalogue workflows
9. Journal entries
10. Lists, list items, and curators
11. Import/export and cleanup workflows

**For each catalogue group:**

- Models and database constraints
- Admin configuration
- Service/query layer
- Schemas and API endpoints
- Authorization
- OpenAPI
- Tests
- Frontend integration

> Build Django admin alongside the models, not after all API endpoints. Admin usability will expose awkward relationships and missing domain operations early.

---

## 10. Cut over deliberately

When Django covers the required flows:

- Run Phoenix and Django against separate databases.
- Import the same seed catalogue.
- Compare representative responses.
- Run the Svelte end-to-end suite against Django.
- Test uploads, email, task retries, search, and admin.
- Document rollback.
- Switch the frontend API origin.
- Keep `backend-phoenix` read-only until the Django deployment has proved stable.

---

## The next implementation commits

The starter adoption is complete. Continue with:

```
docs: define retained subsystems and API compatibility policy
refactor: establish UUID-based foundational models
```

# Background jobs

The starter uses [Procrastinate](https://procrastinate.readthedocs.io/) for
background and periodic work. Jobs, schedules, locks, retries, and worker state
live in the same PostgreSQL service that Django already requires. No separate
broker or cache service is required.

Run one worker for the starter's three queues:

```sh
uv run python manage.py procrastinate worker --queues=email,exports,maintenance
```

The worker also schedules the periodic cleanup and export-recovery tasks. Apply
Django migrations before starting it, because Procrastinate installs its schema
through Django migrations. Use `python manage.py procrastinate healthchecks` to
verify the database, migrations, application, and worker configuration.

## Delivery model

Tasks may execute more than once. Keep task entry points thin, put domain state
transitions in ordinary functions, and make side effects idempotent or protect
them with durable state. Enqueue work with `core.task_queue.defer_task` so the
current request ID reaches worker logs.

Email retries transient connection failures. Export processing uses durable job
state, deterministic object keys, heartbeats, and a PostgreSQL advisory lock.
Successful Procrastinate job records are retained for 14 days by default;
failed, cancelled, and aborted records are retained for 90 days. Job arguments
can contain personal data, so restrict database access and shorten these windows
when the product permits it.

## Migrating an existing Celery deployment

Queued Celery messages are not converted into Procrastinate jobs. Before
deploying this version:

1. Stop new Celery publication and drain the Celery queues.
2. Stop Celery workers and Beat.
3. Deploy the new application and apply Django migrations.
4. Start the Procrastinate worker and run its health checks.
5. Remove legacy Celery/Beat tables only after backup and verification.

Use Celery instead when the product needs broker independence, Celery-specific
workflow primitives, or must integrate with an existing Celery platform. For
the PostgreSQL-backed products targeted by this starter, Procrastinate is the
simpler default.

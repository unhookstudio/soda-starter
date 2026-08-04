# Listening Journal API

The Django Ninja backend for Listening Journal, an organization-scoped music
catalogue and listening journal.

This repository is the foundation for the Python rewrite of the existing
Phoenix API. The first migration phase retains the proven account,
organization, contact, media, storage, and operational infrastructure while the
catalogue and journal domains are ported incrementally.

The current foundation includes:

- Django Ninja and PostgreSQL;
- first-party email/password authentication for native and browser clients;
- rotating, revocable JWT sessions and browser cookie/CSRF flows;
- organization roles, contacts, tags, and private images;
- durable idempotency and asynchronous organization exports;
- S3-compatible private storage and expiring image shares;
- Redis, Celery, and Beat for background work; and
- a single-host production Compose example behind Caddy.

Some inherited subsystems will be removed or replaced as the rewrite's product
boundaries are finalized. Dormant routes and applications must not remain in a
production deployment.

## Local development

Requirements: Python 3.14, [uv](https://docs.astral.sh/uv/), Docker, and Docker
Compose.

```sh
cp env.example .env
docker compose up -d db redis
uv sync --frozen
uv run python manage.py migrate
uv run python manage.py seed_demo --password local-demo-password
uv run python manage.py runserver
```

- API: `http://localhost:8000/api/v1/`
- OpenAPI UI: `http://localhost:8000/api/v1/docs`
- Health: `http://localhost:8000/health/live/` and `/health/ready/`
- Admin: `http://localhost:8000/admin/`

Run Celery when working on email, exports, or scheduled cleanup:

```sh
uv run celery -A listening_journal worker -l INFO --queues=celery,email,exports,maintenance
uv run celery -A listening_journal beat -l INFO --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

Development email is written to the console. Media workflows require the
configured private S3-compatible bucket; tests use isolated local storage.

## Verification

```sh
uv run pytest -q
uv run mypy .
uv run black --check .
uv run isort --profile black --check-only .
uv run flake8 --select=E9,F63,F7,F82 --exclude=.venv,migrations .
uv run python manage.py makemigrations --check --dry-run
uv run python manage.py check --database default
uv run pip-audit
```

CI also tests PostgreSQL, Redis, SMTP, S3-compatible storage, migrations,
production settings, the container image, OpenAPI drift, and secret scanning.

## Current operating assumptions

- Native clients receive refresh tokens in JSON. Browser clients use the
  separate HttpOnly-cookie and CSRF contract in [security.md](docs/security.md).
- Organization `member` is currently an editor role, not a read-only role.
- Django superusers are audited cross-tenant platform administrators; ordinary
  staff receives no tenant bypass.
- Images, exports, and avatars use private storage. Any authenticated user may
  request a short-lived user/contact avatar URL; anonymous media access requires
  an explicit image share.
- PostgreSQL is part of the application contract. PostGIS is optional.
- Redis is currently disposable cache and broker state. PostgreSQL remains
  authoritative for domain data, sessions, idempotency, and jobs.

These assumptions are reviewed as part of the rewrite. Changes must update
authorization, schemas, tests, OpenAPI, deployment configuration, and client
behavior together.

## Deployment

[compose.production.yaml](compose.production.yaml) is a single-host example
running Caddy, web, worker, Beat, PostgreSQL, and Redis. It is suitable only when
single-host failure is acceptable and operations have a named owner; it is not
a high-availability design.

See [deployment.md](docs/deployment.md) and [operations.md](docs/operations.md).

## Documentation

- [Architecture](docs/architecture.md)
- [API routes](docs/api-routes.md)
- [Authentication and security](docs/security.md)
- [Environment variables](docs/environment.md)
- [Production deployment](docs/deployment.md)
- [Operations and recovery](docs/operations.md)
- [Optional PostGIS](docs/postgis.md)
- [Upgrade policy](docs/upgrades.md)

Python 3.14 and Django 6.0 are the currently supported runtime line. Report
vulnerabilities privately as described in [SECURITY.md](SECURITY.md).

Licensed under the [MIT License](LICENSE).

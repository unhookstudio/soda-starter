# SODA Starter

Somewhat Opinionated Django API Starter.

An opinionated starting point for organization-scoped Django Ninja APIs. It
provides a hardened baseline and explicit operating assumptions; it does not
make a derived product production-ready without product-specific review.

Included by design:

- Django Ninja, PostgreSQL, Redis, Celery, and Beat;
- first-party email/password authentication for native and browser clients;
- rotating, revocable JWT sessions and browser cookie/CSRF flows;
- organization roles, contacts, tags, private images, and authenticated avatars;
- durable idempotency and asynchronous organization exports;
- S3-compatible private storage and explicit expiring image shares;
- a single-host production Compose example behind Caddy.

## Fit

This starter fits organization-scoped products that need first-party auth,
private media, and background jobs. It is a poor fit for a small read-only
service, a project that does not use PostgreSQL, or a team seeking a minimal
Django skeleton.

Delete unused applications and subsystems rather than leaving dormant routes in
production. New starter revisions do not preserve backward compatibility for
projects that have already been derived from an older revision.

## Start a project

Create a repository from this GitHub template, then follow the
[adoption and renaming guide](docs/adoption.md). For example:

```sh
uv run python scripts/rename_project.py gallery_tours \
  --distribution gallery-tours-api \
  --display-name "Gallery Tours"
```

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
- health: `http://localhost:8000/health/live/` and `/health/ready/`

Run Celery when working on email, exports, or scheduled cleanup:

```sh
uv run celery -A DjangoApiStarter worker -l INFO --queues=celery,email,exports,maintenance
uv run celery -A DjangoApiStarter beat -l INFO --scheduler django_celery_beat.schedulers:DatabaseScheduler
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

## Defaults to review

- Native clients receive refresh tokens in JSON. Browser clients use the
  separate HttpOnly-cookie and CSRF contract in [security.md](docs/security.md).
- Organization `member` is an editor role, not a read-only role.
- Django superusers are audited cross-tenant platform administrators; ordinary
  staff receives no tenant bypass.
- Images, exports, and avatars use private storage. Any authenticated user may
  request a short-lived user/contact avatar URL; anonymous media access requires
  an explicit image share.
- PostgreSQL is part of the contract. PostGIS is optional.
- Redis is disposable cache/broker state. PostgreSQL remains authoritative for
  domain data, sessions, idempotency, and jobs.

Review authorization, privacy, abuse prevention, availability, backups,
restoration, monitoring, and compliance for every derived product.

## Deployment

[compose.production.yaml](compose.production.yaml) is a maintained single-host
example running Caddy, web, worker, Beat, PostgreSQL, and Redis. It is suitable
only when single-host failure is acceptable and operations have a named owner;
it is not a high-availability design.

See [deployment.md](docs/deployment.md) and [operations.md](docs/operations.md).

## Documentation

- [Architecture](docs/architecture.md)
- [API routes](docs/api-routes.md)
- [Authentication and security](docs/security.md)
- [Environment variables](docs/environment.md)
- [Adopting and renaming the starter](docs/adoption.md)
- [Production deployment](docs/deployment.md)
- [Operations and recovery](docs/operations.md)
- [Optional PostGIS](docs/postgis.md)
- [Upgrade policy](docs/upgrades.md)

## Maintenance

Python 3.14 and Django 6.0 are the currently supported runtime line. The starter
is maintained primarily for its contributors' own projects. Issues and pull
requests are welcome as time permits, but there is no support SLA or stable API
compatibility promise. Report vulnerabilities privately as described in
[SECURITY.md](SECURITY.md).

Licensed under the [MIT License](LICENSE).

# Start a project from the template

Create a new repository from the GitHub template or clone this repository into
a new private repository. Do not build an application directly on a checkout
that still tracks the starter's `main` branch.

## Rename the project

Use a lower-case Python package name with underscores, a hyphenated repository
or distribution name, and a human-readable display name:

```sh
uv run python scripts/rename_project.py gallery_tours \
  --distribution gallery-tours-api \
  --display-name "Gallery Tours"
```

The command updates the starter identifiers in text files and renames the
`DjangoApiStarter/` package. Preview its changes with `--dry-run`. It refuses to
overwrite an existing target package or accept an invalid Python/distribution
name.

Review the result rather than treating renaming as product configuration:

```sh
rg 'DjangoApiStarter|soda-starter|SODA Starter|Somewhat Opinionated Django API Starter' \
  --glob '!.venv/**' --glob '!.git/**'
git diff --stat
```

Occurrences inside `scripts/rename_project.py` and this guide are intentional.
Delete the renaming script and starter release checklists from a derived product
if they no longer provide value.

## Choose the product boundaries

Before adding models, record which starter decisions the product keeps:

- organization roles and whether `member` remains an editor;
- first-party authentication and native/browser client contracts;
- globally visible-to-authenticated-users avatars;
- explicit anonymous image sharing;
- Celery/Redis background work;
- the single-host Compose deployment example.

Delete unused sample applications and their routes, settings, migrations, tests,
and documentation together. Do not leave dormant endpoints in production.

## Establish a clean baseline

Copy the environment template, start PostgreSQL and Redis, and verify the
renamed project before product work:

```sh
cp env.example .env
docker compose up -d db redis
uv sync --frozen
uv run python manage.py migrate
uv run python manage.py check --database default
uv run pytest -q
uv run mypy .
```

Regenerate `docs/openapi.json` after intentionally changing routes or schemas.
Commit the rename and any removed starter applications as a standalone baseline
so later product changes remain reviewable.

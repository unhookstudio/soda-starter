# Public Release Checklist

## Purpose

This document describes the work required before making
`soda-starter` public.

The repository is intended to be a production-oriented, batteries-included
starting point for organization-scoped Django Ninja APIs. Publishing it should
make the architecture and tradeoffs visible without implying that an
application generated from it is automatically production-ready.

Do not change the GitHub repository visibility until the blocking items below
are complete.

## 1. Remove tracked development artifacts

The repository previously tracked development artifacts that should not be part
of the public template:

- `.coverage`
- generated files under `.test_media/`
- PyCharm/IntelliJ metadata under `.idea/`

They have been removed from the Git index. `.coverage`, `.test_media/`, and
`.idea/` are ignored, and the obsolete personal `.windsurf` instructions have
been deleted. Retain the verification below as a release check.

Example verification:

```sh
git ls-files .coverage '.test_media/**' '.idea/**' .windsurf
git status --ignored --short
```

After cleanup, running the complete test suite must not leave new tracked or
non-ignored media, coverage, database, log, or editor artifacts. Tests should
clean up generated media where practical, but files confined to an intentional
ignored test directory are not by themselves a publication blocker.

## 2. Audit the complete Git history for secrets

Making a repository public exposes every object reachable from its branches
and tags, not only the current working tree.

The CI workflow already checks out the full history and runs Gitleaks. Before
publication:

1. Confirm the latest Gitleaks job passes on the default branch.
2. Run a second full-history scan locally or through another trusted scanner.
3. Inspect old deployment commits for credentials, hostnames, email addresses,
   storage endpoints, private bucket names, signing keys, and access tokens.
4. Confirm that all values in example and CI configuration are unmistakably
   placeholders or isolated test credentials.
5. Check every remote branch and tag that will be publicly reachable, not only
   `main`.

If a real secret ever entered Git history, revoking or rotating it is mandatory.
Removing the string from the current version is not sufficient. Rewrite history
only after rotation, then force-update every affected remote reference and ask
all existing users to replace their clones.

For the initial SODA release, use the clean repository initialized at
`soda-starter` rather than changing the visibility of the historical
private repository. The release repository must contain only the reviewed
initial commit and subsequent public-safe work. Do not push branches, tags, or
objects from the historical repository into it. Keep the old repository private
or delete it after retaining any required local archive. This clean-history
approach limits what is published, but it does not remove the requirement to
revoke or rotate any credential that appeared in the historical repository.

Do not print suspected secrets into CI logs, issues, or review comments while
investigating them.

## 3. Add an explicit license

The repository uses the MIT License. Confirm that all committed code and assets
can legally be released under it, retain `LICENSE` at the repository root, and
keep the README reference accurate.

Without an explicit license, public visibility allows people to inspect the
source but does not clearly grant permission to copy, modify, or redistribute
it.

## 4. Clarify the project's scope and support contract

The README should make the following points obvious near the top:

- This is an opinionated starting point, not a framework.
- It provides a hardened baseline but does not make a derived application
  production-ready by itself.
- Adopters must review authorization, privacy, abuse prevention, availability,
  backups, restoration, monitoring, and compliance for their product.
- Redis, Celery, Beat, PostgreSQL, and S3-compatible storage are intentional
  parts of this starter's architecture.
- Unneeded applications and subsystems should be deleted rather than left
  dormant.
- Backward compatibility is not guaranteed when beginning a new application
  from a later revision of the starter.
- Private media is the default. Avatars are available to authenticated users,
  not anonymously accessible through a public object-storage bucket.

Add a short "Good fit / Poor fit" section. For example, the starter is a good
fit for organization-scoped APIs needing first-party authentication, private
media, and background jobs. It is a poor fit for a small read-only service,
projects that do not use PostgreSQL, or teams that want a minimal Django
skeleton.

State the expected maintenance posture:

- whether issues and pull requests are welcome;
- whether releases or semantic versioning will be used;
- which Python and Django versions are supported;
- whether security reports should be public or private;
- whether the project is maintained for personal use or offered with community
  support expectations.

## 5. Review documentation for private or stale material

Read every committed Markdown file as if encountering the project for the first
time. In particular, review:

- deployment and operations documentation
- the production-readiness checklist
- environment-variable documentation
- security documentation
- comments and examples copied from earlier private applications

Remove internal planning notes, personal infrastructure details, abandoned
instructions, and references that require private context. Ensure commands,
paths, image tags, package versions, and environment-variable names agree with
the current implementation.

Do not include architecture commentary about private downstream applications.
Product-specific decisions belong in those products, not in the reusable
starter's public documentation.

The generated OpenAPI document must match the application and should not
contain internal server URLs, private descriptions, sample personal data, or
unintended administrative endpoints.

## 6. Review example configuration and deployment defaults

Example configuration should be safe to copy without looking like real
credentials.

Verify that:

- development defaults cannot accidentally be accepted by production settings;
- `SECRET_KEY` and `JWT_SIGNING_KEY` are required and independent in production;
- production database, Redis, SMTP, and object-storage credentials are required;
- the deployment requires only a private object-storage bucket unless a derived
  product deliberately introduces anonymous public media;
- debug mode is disabled in production;
- allowed hosts, CORS, CSRF, cookies, CSP, TLS expectations, and proxy headers
  are documented;
- test credentials cannot reach real services;
- containers run with appropriate users and have bounded health checks;
- dependency and container-image pins are intentional and maintainable;
- backup and restore instructions have been exercised, not merely documented.

The single-host Compose file should remain clearly labeled as an example for
deployments where single-host failure is acceptable, not as a high-availability
design.

## 7. Reassess reusable security boundaries

Conduct a final review of the behaviors most likely to be copied into derived
applications:

- registration and email verification;
- password reset and email change;
- JWT issuance, rotation, revocation, expiry, issuer, and audience validation;
- browser cookie and CSRF behavior;
- account deactivation and deletion;
- organization membership changes and last-owner protection;
- platform-administrator tenant access and audit logging;
- cross-tenant lookup behavior and not-found responses;
- upload size, content, pixel, filename, and object-key validation;
- authenticated avatar access and private media storage boundaries;
- signed URL expiry and image-share revocation;
- throttling of authentication, recovery, upload, and mutation endpoints;
- idempotency keys and transaction boundaries;
- asynchronous retry safety and duplicate execution;
- export authorization, retention, cleanup, and failure recovery.

Document important delivery guarantees. Celery tasks must be written with the
assumption that they can execute more than once. Side-effecting handlers should
therefore be idempotent or protected by durable state.

## 8. Verify dependency and supply-chain hygiene

Keep the existing dependency audit and container scan green. Before release:

```sh
uv sync --frozen
uv run pip-audit
```

Review direct dependencies and remove any that are no longer used. Confirm that
Dependabot is configured for the package and container ecosystems actually in
the repository.

Pinned GitHub Actions and container images should be intentional. Establish a
routine for refreshing pins so digest pinning does not silently turn into
permanent use of obsolete software.

## 9. Run the complete release verification

Run all documented checks from a clean checkout using the supported Python
version:

```sh
uv sync --frozen
uv run pytest -q
uv run black --check .
uv run isort --profile black --check-only .
uv run flake8 --select=E9,F63,F7,F82 .
uv run mypy .
uv run python manage.py makemigrations --check --dry-run
uv run python manage.py check --database default
uv run pip-audit
```

Every command presented as a required check must also run in CI. In particular,
add the `isort --check-only` invocation to CI rather than relying on developers
to remember it locally.

Also verify the workflows CI performs:

- apply migrations twice;
- regenerate and compare OpenAPI;
- run Django production deployment checks;
- build and scan the production image;
- start the image and pass the health-check smoke test;
- exercise PostgreSQL, Redis, SMTP, and S3-compatible providers;
- run the configured secret scan.

The ordinary CI secret scan may inspect only the pushed revision range. The
separate full-history, all-public-ref scan in section 2 remains a release gate.

Test the README setup instructions from a fresh clone. A successful setup in the
developer's existing working directory is not sufficient evidence that the
starter is reproducible.

Also test the repository as a template rather than only as itself:

1. Create a disposable repository from a clean copy.
2. Rename the `DjangoApiStarter` Python package to a realistic project package.
3. Update settings, Celery, ASGI/WSGI, scripts, Compose, and documentation
   references using the documented adoption procedure.
4. Search for unintended `DjangoApiStarter`, repository-name, demo-domain, and
   placeholder references.
5. Run setup, migrations, checks, and tests in the renamed project.

Document the supported renaming procedure in the README or a short dedicated
adoption guide. If consumers are not expected to rename the package, state that
explicitly instead.

## 10. Add public repository metadata

Before or immediately after changing visibility:

- add a concise GitHub repository description;
- add relevant topics such as `django`, `django-ninja`, `postgresql`, `celery`,
  `redis`, `jwt`, and `starter-template`;
- mark the repository as a GitHub template if that is the intended consumption
  model;
- configure the issue tracker and pull-request policy;
- add `SECURITY.md` with a private vulnerability-reporting route;
- optionally add `CONTRIBUTING.md` and a code of conduct if outside
  contributions are welcome;
- enable dependency and secret alerts supported by GitHub;
- verify branch protection and required checks for `main`;
- ensure the repository homepage and social preview do not expose private data.

## 11. Final publication gate

### Verification record (2026-08-04)

The clean-history release repository was verified independently of the
historical checkout:

- Gitleaks scanned its complete history with no findings.
- The locked environment installed from scratch with Python 3.14.
- 405 tests passed and 9 provider-dependent tests were skipped in the local
  SQLite suite.
- mypy, Black, isort, the configured flake8 checks, migration drift detection,
  and `pip-audit` passed.
- A disposable `gallery_tours` rename passed the same 405-test suite and mypy,
  with no unintended starter identifiers remaining.
- The production image built successfully, ran as the unprivileged application
  user on a read-only filesystem, and passed its live health check.
- Trivy 0.70.0 reported no fixed HIGH or CRITICAL vulnerabilities in the image.
- The PostgreSQL suite, Redis/SMTP/S3 provider smoke checks, production Django
  deployment check, and encrypted PostgreSQL backup/restore exercise passed
  against the release snapshot before the branding-only commit.

The first GitHub Actions run in the new repository remains a publication gate;
local results are not a substitute for verifying the hosted workflow and its
repository settings.

The repository can be made public when all of the following are true:

- [x] Generated test media, coverage data, and local IDE state are no longer
      tracked.
- [x] Every branch and tag in the clean release repository passes a full-history
      secret audit.
- [ ] Any previously exposed secret has been revoked or rotated.
- [x] An explicit license is present.
- [x] README scope, limitations, supported versions, and maintenance expectations
      are clear.
- [x] Avatars and ordinary media use private storage; anonymous access is only
      possible through an explicit, time-limited or revocable sharing feature.
- [x] All documentation has been reviewed for private and stale information.
- [x] Production examples fail closed when required configuration is missing.
- [x] Authentication, tenant isolation, media access, task retries, and exports
      have received a final security review.
- [ ] Tests, typing, Black, isort, migrations, Django checks, OpenAPI comparison,
      dependency audit, image scan, smoke test, and secret scan pass in CI.
- [x] Setup instructions succeed from a fresh repository checkout.
- [x] The documented project-renaming procedure succeeds in a disposable copy,
      with no unintended starter identifiers left behind.
- [ ] GitHub security reporting, alerts, repository metadata, and branch rules are
      configured.

After changing visibility, inspect the repository while logged out or in a
private browser window. Confirm that the README, documentation links, Actions
logs, releases, branches, tags, issues, and downloadable artifacts reveal only
what was intended.

# API contract decision

Listening Journal exposes a first-party JSON API below `/api/v1`. The contract
is designed for the long-lived Django/Svelte application; it does not preserve
Phoenix or starter-template shapes merely for migration compatibility.

## Resource and routing conventions

- Paths use plural nouns, lowercase kebab-case, and no trailing slash.
- Public identifiers are UUIDs. Slugs are presentation data and are reserved
  for intentionally public, human-readable pages.
- The public tenant term is **workspace**. The Django `Organization` model is an
  internal implementation detail.
- Workspace-owned resources are explicitly scoped below
  `/workspaces/{workspace_id}`. The current workspace is a UI preference, never
  an implicit authorization or mutation scope.
- Successful resources are returned directly. There is no universal `data`
  envelope.
- Create operations return `201`; accepted asynchronous work returns `202`;
  successful commands without a useful representation return `204`.
- Current bounded collections use `{items, count}` with `limit` and `offset`.
  Future mutable feeds such as journal timelines may define cursor pagination
  explicitly rather than changing the meaning of limit/offset.

## Authentication and identity

Authentication actions live below `/auth`: login, refresh, logout,
registration verification, password reset, and email verification. Token
responses use `access_token`, `refresh_token`, `token_type`, and `expires_in`.
Refresh tokens rotate and every token remains bound to a revocable server-side
session.

`/auth/me` is the authenticated profile resource. `/workspaces/current` stores
the user's preferred workspace. Every workspace-owned request still carries an
explicit workspace UUID, preventing one tab or device from redirecting another
tab's writes by changing global preference state.

## Errors

Every API failure uses `application/problem+json` and a Problem Details-inspired
object:

```json
{
  "type": "urn:listening-journal:problem:validation-error",
  "title": "Request validation failed",
  "status": 422,
  "detail": "One or more request values are invalid.",
  "code": "validation_error",
  "instance": "/api/v1/auth/register",
  "request_id": "8b21d6b0d8d947bfa64791aa938fc6b0",
  "errors": [
    {"code": "value_error", "message": "Invalid email", "field": "email"}
  ]
}
```

`code` and each nested error code are machine-readable. `detail` and messages
are for people and may be reworded. Validation failures use `422`; malformed
JSON and semantically invalid commands use `400`; conflicts use `409`.
Authentication, authorization, missing-resource, throttling, and service
failures retain their corresponding HTTP status.

The server returns the request ID in both the response header and error body.
Unexpected failures never expose exception internals.

## Current route families

| Area | Routes |
| --- | --- |
| Authentication | `/auth/login`, `/auth/refresh`, `/auth/token/verify`, `/auth/logout`, `/auth/logout-all`, registration, email, and password-reset commands |
| Profile | `/auth/me`, `/auth/me/avatar`, `/auth/me/username` |
| Workspaces | `/workspaces`, `/workspaces/current` |
| Contacts | `/workspaces/{workspace_id}/contacts` and contact/avatar resources by UUID |
| Tags | Workspace tag resources and `/objects/{app_label}/{model}/{object_id}/tags` |
| Images | Workspace image resources and `/objects/{app_label}/{model}/{object_id}/images` |
| Exports | `/workspaces/{workspace_id}/exports` |
| Public image shares | `/image-shares/resolve` |

The generated `openapi.json` is authoritative for exact payloads and is checked
for drift in CI.

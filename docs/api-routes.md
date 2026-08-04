# API routes and conventions

The generated [OpenAPI contract](openapi.json) is authoritative. CI regenerates
it and fails on drift. Interactive documentation is mounted at `/api/v1/docs`;
API operations are versioned below `/api/v1`.

The design rationale and compatibility policy live in
[02_api_contract.md](02_api_contract.md).

## Conventions

- Workspace-owned resources use `/workspaces/{workspace_id}/...` with UUIDs.
- A resource belonging to another workspace is treated as not found.
- Successful resources are returned directly. Paginated collections use
  `{items, count}` with limit/offset pagination.
- Errors use `application/problem+json` and include `type`, `title`, `status`,
  `detail`, `code`, and `instance`; request IDs and field errors are included
  when available.
- Schema validation failures return `422`, uniqueness conflicts return `409`,
  and successful commands without a response body return `204`.
- Breaking changes require a new API version and regenerated OpenAPI.

## Route groups

| Purpose | Routes |
| --- | --- |
| Sessions | `POST /auth/login`, `/auth/refresh`, `/auth/token/verify`, `/auth/logout`, `/auth/logout-all` |
| Account lifecycle | Registration, verification, email-change, password-reset, password-change, and `DELETE /auth/me` |
| Current user | `GET/PATCH /auth/me`, avatar and username below `/auth/me`; public user avatars below `/users/{user_id}/avatar` |
| Workspaces | `GET /workspaces`, `GET/PUT /workspaces/current` |
| Contacts | Collection and UUID CRUD below `/workspaces/{workspace_id}/contacts`; avatars remain in the same scope |
| Tags | Collection CRUD below `/workspaces/{workspace_id}/tags`; object assignments below `/workspaces/{workspace_id}/objects/.../tags` |
| Images | Media library below `/workspaces/{workspace_id}/images`; relations and cover images below `/workspaces/{workspace_id}/objects/...` |
| Public shares | `POST /image-shares/resolve` with the raw token in the body |
| Exports | Collection, status, download, and retry below `/workspaces/{workspace_id}/exports` |

Authenticated routes accept `Authorization: Bearer <access-token>`. Token
responses use `access_token`, `refresh_token`, `token_type`, and `expires_in`.
The SvelteKit server stores those tokens in its own browser-facing HttpOnly
cookies; see [security.md](security.md).

Export creation returns a job, not a URL. Poll the authenticated job route; a
ready response contains a short-lived signed download URL. Export files expire
after `EXPORT_RETENTION_DAYS` and the maintenance task deletes the object.

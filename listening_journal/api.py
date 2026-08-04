import orjson
from django.http import Http404
from ninja.errors import HttpError
from ninja.errors import ValidationError as NinjaValidationError
from ninja.renderers import BaseRenderer
from ninja_extra import NinjaExtraAPI

from accounts.api import auth_router
from accounts.users_api import profile_router, users_router
from contacts.api import contacts_router
from core.api_errors import (
    http_error_response,
    not_found_response,
    unhandled_error_response,
    validation_error_response,
)
from core.schemas import ProblemDetails
from images.api import router as images_router
from organizations.api import workspace_router
from organizations.api_export import export_router
from tags.api import router as tags_router


# Custom ORJSON Renderer
class ORJSONRenderer(BaseRenderer):
    media_type = "application/json"

    def render(self, request, data, *, response_status):
        return orjson.dumps(data)


class ListeningJournalAPI(NinjaExtraAPI):
    def get_openapi_schema(self, *, path_prefix=None, path_params=None):
        schema = super().get_openapi_schema(
            path_prefix=path_prefix,
            path_params=path_params,
        )
        problem_schema = ProblemDetails.model_json_schema(
            ref_template="#/components/schemas/{model}"
        )
        definitions = problem_schema.pop("$defs", {})
        components = schema.setdefault("components", {})
        components.setdefault("schemas", {}).update(definitions)
        components["schemas"]["ProblemDetails"] = problem_schema
        components.setdefault("responses", {})["ProblemDetails"] = {
            "description": "Request failed",
            "content": {
                "application/problem+json": {
                    "schema": {"$ref": "#/components/schemas/ProblemDetails"}
                }
            },
        }
        for path in schema.get("paths", {}).values():
            for operation in path.values():
                if not isinstance(operation, dict) or "responses" not in operation:
                    continue
                operation["responses"] = {
                    str(status): response
                    for status, response in operation["responses"].items()
                }
                operation["responses"].setdefault(
                    "default",
                    {"$ref": "#/components/responses/ProblemDetails"},
                )
        return schema


api = ListeningJournalAPI(
    renderer=ORJSONRenderer(),
    urls_namespace="api",
    version="v1",
    title="Listening Journal",
    description="Listening Journal",
)

auth_router.add_router("", profile_router, tags=["profile"])
api.add_router("/auth", auth_router)
api.add_router("/users", users_router, tags=["users"])
api.add_router("/workspaces", workspace_router)
api.add_router("/", contacts_router, tags=["contacts"])
api.add_router("/", tags_router, tags=["tags"])
api.add_router("/", images_router)
api.add_router("/", export_router, tags=["organization", "export"])
# Register error handlers (especially for validation errors)
api.add_exception_handler(NinjaValidationError, validation_error_response)
api.add_exception_handler(HttpError, http_error_response)
api.add_exception_handler(Http404, not_found_response)
api.add_exception_handler(Exception, unhandled_error_response)

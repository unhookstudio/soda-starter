from datetime import datetime

from ninja import Schema
from pydantic import ConfigDict


class DetailResponse(Schema):
    detail: str


class AvatarUrlsOut(Schema):
    small: str
    large: str
    expires_at: datetime


class ProblemError(Schema):
    code: str
    message: str
    field: str | None = None


class ProblemDetails(Schema):
    type: str
    title: str
    status: int
    detail: str
    code: str
    instance: str
    request_id: str | None = None
    errors: list[ProblemError] | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "urn:listening-journal:problem:validation-error",
                "title": "Request validation failed",
                "status": 422,
                "detail": "One or more request values are invalid.",
                "code": "validation_error",
                "instance": "/api/v1/auth/register",
                "request_id": "8b21d6b0d8d947bfa64791aa938fc6b0",
                "errors": [
                    {
                        "code": "value_error",
                        "message": "Invalid email",
                        "field": "email",
                    }
                ],
            }
        }
    )

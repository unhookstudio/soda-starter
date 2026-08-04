import logging
from http import HTTPStatus

from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from ninja.errors import HttpError, Throttled, ValidationError

from core.error_reporting import report_exception

logger = logging.getLogger(__name__)

STATUS_CODES = {
    400: "invalid_request",
    401: "authentication_required",
    403: "permission_denied",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    413: "payload_too_large",
    422: "validation_error",
    429: "rate_limited",
    500: "internal_server_error",
    503: "service_unavailable",
}

STATUS_TITLES = {
    400: "Invalid request",
    401: "Authentication required",
    403: "Permission denied",
    404: "Resource not found",
    409: "Request conflict",
    422: "Request validation failed",
    429: "Too many requests",
    500: "Internal server error",
    503: "Service unavailable",
}


class ApiError(HttpError):
    def __init__(self, status_code: int, code: str, detail: str) -> None:
        self.code = code
        super().__init__(status_code, detail)


def _request_id(request: HttpRequest) -> str | None:
    return getattr(request, "request_id", None)


def _problem_response(
    request: HttpRequest,
    *,
    status: int,
    detail: str,
    code: str | None = None,
    title: str | None = None,
    errors: list[dict] | None = None,
    headers: dict[str, str] | None = None,
) -> JsonResponse:
    code = code or STATUS_CODES.get(status, "request_failed")
    try:
        fallback_title = HTTPStatus(status).phrase
    except ValueError:
        fallback_title = "Request failed"
    payload = {
        "type": f"urn:listening-journal:problem:{code.replace('_', '-')}",
        "title": title or STATUS_TITLES.get(status, fallback_title),
        "status": status,
        "detail": detail,
        "code": code,
        "instance": request.path,
    }
    request_id = _request_id(request)
    if request_id:
        payload["request_id"] = request_id
    if errors:
        payload["errors"] = errors
    response = JsonResponse(
        payload,
        status=status,
        content_type="application/problem+json",
    )
    for name, value in (headers or {}).items():
        response[name] = value
    return response


def _validation_field(location) -> str | None:
    parts = [str(part) for part in location if str(part) not in {"body", "data"}]
    return ".".join(parts) or None


def validation_error_response(
    request: HttpRequest, exc: ValidationError | type[ValidationError]
) -> HttpResponse:
    if isinstance(exc, type):
        exc = exc([])
    errors = [
        {
            "code": str(item.get("type", "validation_error")),
            "message": str(item.get("msg", "Invalid value")),
            "field": _validation_field(item.get("loc", ())),
        }
        for item in exc.errors
    ]
    return _problem_response(
        request,
        status=422,
        detail="One or more request values are invalid.",
        code="validation_error",
        errors=errors,
    )


def http_error_response(
    request: HttpRequest, exc: HttpError | type[HttpError]
) -> HttpResponse:
    if isinstance(exc, type):
        exc = exc(500, "Internal server error")
    detail = getattr(exc, "detail", None)
    if isinstance(detail, dict):
        detail = detail.get("detail")
    detail = str(detail or exc)
    headers = None
    if isinstance(exc, Throttled) and exc.wait is not None:
        headers = {"Retry-After": str(max(int(exc.wait), 1))}
    return _problem_response(
        request,
        status=exc.status_code,
        detail=detail,
        code=getattr(exc, "code", None),
        headers=headers,
    )


def not_found_response(
    request: HttpRequest, exc: Http404 | type[Http404]
) -> HttpResponse:
    return _problem_response(
        request,
        status=404,
        detail="The requested resource was not found.",
    )


def unhandled_error_response(
    request: HttpRequest, exc: Exception | type[Exception]
) -> HttpResponse:
    if isinstance(exc, type):
        exc = exc()
    request_id = _request_id(request)
    context = {
        "request_id": request_id,
        "method": request.method,
        "path": request.path,
    }
    logger.error(
        "Unhandled API exception",
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    report_exception(exc, context=context)
    return _problem_response(
        request,
        status=500,
        detail="An unexpected error occurred.",
    )

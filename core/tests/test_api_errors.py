import json
from unittest.mock import patch

from django.test import RequestFactory

from core.api_errors import unhandled_error_response


def test_unhandled_error_is_generic_and_reports_request_context():
    request = RequestFactory().get("/api/v1/example/")
    request.request_id = "request-123"
    exception = RuntimeError("sensitive internal detail")

    with patch("core.api_errors.report_exception") as reporter:
        response = unhandled_error_response(request, exception)

    assert response.status_code == 500
    assert response["Content-Type"] == "application/problem+json"
    assert json.loads(response.content) == {
        "type": "urn:listening-journal:problem:internal-server-error",
        "title": "Internal server error",
        "status": 500,
        "detail": "An unexpected error occurred.",
        "code": "internal_server_error",
        "instance": "/api/v1/example/",
        "request_id": "request-123",
    }
    reporter.assert_called_once_with(
        exception,
        context={
            "request_id": "request-123",
            "method": "GET",
            "path": "/api/v1/example/",
        },
    )

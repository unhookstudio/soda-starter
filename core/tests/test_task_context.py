from unittest.mock import Mock

from core.task_queue import defer_task, task_request_context
from core.utils.logging import request_id_context


def test_request_id_is_added_to_deferred_task_payload():
    task = Mock()
    task.defer.return_value = 42
    token = request_id_context.set("request-123")
    try:
        assert defer_task(task, value="payload") == 42
    finally:
        request_id_context.reset(token)

    task.defer.assert_called_once_with(
        request_id="request-123",
        value="payload",
    )


def test_task_request_context_is_bound_only_during_task_execution():
    token = request_id_context.set(None)
    try:
        with task_request_context("request-123"):
            assert request_id_context.get() == "request-123"
        assert request_id_context.get() is None
    finally:
        request_id_context.reset(token)

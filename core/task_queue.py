from contextlib import contextmanager

from core.utils.logging import request_id_context


def defer_task(task, **kwargs) -> int:
    """Enqueue a task while carrying the current request ID into its payload."""
    return task.defer(request_id=request_id_context.get(), **kwargs)


@contextmanager
def task_request_context(request_id: str | None):
    token = request_id_context.set(request_id)
    try:
        yield
    finally:
        request_id_context.reset(token)

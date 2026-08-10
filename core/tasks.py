from smtplib import SMTPConnectError, SMTPServerDisconnected

import procrastinate
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from procrastinate.contrib.django import app
from procrastinate.job_context import JobContext

from core.models import IdempotencyRecord, RateLimitBucket
from core.task_queue import defer_task, task_request_context


def _send_email_task(
    subject, message, recipient_list, from_email=None, html_message=None
):
    """
    Helper function to send an email using Django's email backend.
    Args:
        subject (str): Email subject
        message (str): Plain text message
        recipient_list (list[str]): List of recipient email addresses
        from_email (str, optional): Sender address (defaults to settings.DEFAULT_FROM_EMAIL)
        html_message (str, optional): HTML message body
    """
    if from_email is None:
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "webmaster@localhost")
    send_mail(
        subject,
        message,
        from_email,
        recipient_list,
        fail_silently=False,
        html_message=html_message,
    )


@app.task(
    queue="email",
    retry=procrastinate.RetryStrategy(
        max_attempts=4,
        exponential_wait=2,
        retry_exceptions={SMTPServerDisconnected, SMTPConnectError, OSError},
    ),
)
def send_email_task(
    subject,
    message,
    recipient_list,
    from_email=None,
    html_message=None,
    request_id=None,
):
    """
    Procrastinate task to send an email asynchronously using Django's backend.
    Args:
        subject (str): Email subject
        message (str): Plain text message
        recipient_list (list[str]): List of recipient email addresses
        from_email (str, optional): Sender address (defaults to settings.DEFAULT_FROM_EMAIL)
        html_message (str, optional): HTML message body
    """
    with task_request_context(request_id):
        _send_email_task(subject, message, recipient_list, from_email, html_message)


def cleanup_expired_idempotency_records() -> int:
    queryset = IdempotencyRecord.objects.filter(expires_at__lte=timezone.now())
    count = queryset.count()
    queryset.delete()
    return count


def cleanup_expired_rate_limit_buckets() -> int:
    queryset = RateLimitBucket.objects.filter(expires_at__lte=timezone.now())
    count = queryset.count()
    queryset.delete()
    return count


async def prune_task_history(context: JobContext) -> None:
    """Keep failures longer than successes while bounding queue-table growth."""
    success_hours = int(getattr(settings, "TASK_HISTORY_RETENTION_HOURS", 24 * 14))
    failure_hours = int(getattr(settings, "TASK_FAILURE_RETENTION_HOURS", 24 * 90))
    await context.app.job_manager.delete_old_jobs(nb_hours=success_hours)
    await context.app.job_manager.delete_old_jobs(
        nb_hours=failure_hours,
        include_failed=True,
        include_cancelled=True,
        include_aborted=True,
    )


def enqueue_email(
    subject, message, recipient_list, from_email=None, html_message=None
) -> int:
    return defer_task(
        send_email_task,
        subject=subject,
        message=message,
        recipient_list=recipient_list,
        from_email=from_email,
        html_message=html_message,
    )


@app.periodic(cron="17 3 * * *")
@app.task(queue="maintenance", queueing_lock="cleanup-idempotency-records")
def cleanup_expired_idempotency_records_task(timestamp: int, request_id=None) -> int:
    with task_request_context(request_id):
        return cleanup_expired_idempotency_records()


@app.periodic(cron="27 3 * * *")
@app.task(queue="maintenance", queueing_lock="cleanup-rate-limit-buckets")
def cleanup_expired_rate_limit_buckets_task(timestamp: int, request_id=None) -> int:
    with task_request_context(request_id):
        return cleanup_expired_rate_limit_buckets()


@app.periodic(cron="47 3 * * *")
@app.task(
    queue="maintenance",
    queueing_lock="prune-task-history",
    pass_context=True,
)
async def prune_task_history_task(
    context: JobContext, timestamp: int, request_id=None
) -> None:
    with task_request_context(request_id):
        await prune_task_history(context)

import asyncio
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

from django.test import override_settings
from django.utils import timezone

from core.models import RateLimitBucket
from core.tasks import cleanup_expired_rate_limit_buckets, prune_task_history


def test_cleanup_expired_rate_limit_buckets(db):
    now = timezone.now()
    RateLimitBucket.objects.create(
        key_hash="expired",
        scope="test",
        identity_hash="identity",
        window_started_at=now - timedelta(minutes=2),
        expires_at=now - timedelta(minutes=1),
    )
    RateLimitBucket.objects.create(
        key_hash="active",
        scope="test",
        identity_hash="identity",
        window_started_at=now,
        expires_at=now + timedelta(minutes=1),
    )

    assert cleanup_expired_rate_limit_buckets() == 1
    assert set(RateLimitBucket.objects.values_list("key_hash", flat=True)) == {"active"}


@override_settings(
    TASK_HISTORY_RETENTION_HOURS=48,
    TASK_FAILURE_RETENTION_HOURS=720,
)
def test_prune_task_history_retains_failures_longer():
    delete_old_jobs = AsyncMock()
    context = SimpleNamespace(
        app=SimpleNamespace(
            job_manager=SimpleNamespace(delete_old_jobs=delete_old_jobs)
        )
    )

    asyncio.run(prune_task_history(context))

    assert delete_old_jobs.await_args_list[0].kwargs == {"nb_hours": 48}
    assert delete_old_jobs.await_args_list[1].kwargs == {
        "nb_hours": 720,
        "include_failed": True,
        "include_cancelled": True,
        "include_aborted": True,
    }

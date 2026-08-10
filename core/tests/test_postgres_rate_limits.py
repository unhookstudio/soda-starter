from datetime import datetime, timedelta, timezone

import pytest

from core.models import RateLimitBucket
from core.throttling import consume_rate_limit


@pytest.mark.django_db
def test_postgres_rate_limit_is_scoped_hashed_and_resets_next_window():
    now = datetime(2026, 8, 10, 12, 0, 10, tzinfo=timezone.utc)

    assert consume_rate_limit(
        scope="login", identity="ip:192.0.2.1", limit=2, window_seconds=60, now=now
    ).allowed
    assert consume_rate_limit(
        scope="login", identity="ip:192.0.2.1", limit=2, window_seconds=60, now=now
    ).allowed
    limited = consume_rate_limit(
        scope="login", identity="ip:192.0.2.1", limit=2, window_seconds=60, now=now
    )

    assert limited.allowed is False
    assert limited.retry_after == 50
    bucket = RateLimitBucket.objects.get()
    assert bucket.scope == "login"
    assert bucket.request_count == 2
    assert bucket.identity_hash != "ip:192.0.2.1"
    assert len(bucket.identity_hash) == 64

    next_window = consume_rate_limit(
        scope="login",
        identity="ip:192.0.2.1",
        limit=2,
        window_seconds=60,
        now=now + timedelta(seconds=50),
    )
    assert next_window.allowed


@pytest.mark.django_db
def test_postgres_rate_limit_separates_scopes_and_identities():
    now = datetime(2026, 8, 10, 12, 0, 10, tzinfo=timezone.utc)

    for scope, identity in (
        ("login", "ip:192.0.2.1"),
        ("login", "ip:192.0.2.2"),
        ("password-reset", "ip:192.0.2.1"),
    ):
        result = consume_rate_limit(
            scope=scope,
            identity=identity,
            limit=1,
            window_seconds=60,
            now=now,
        )
        assert result.allowed

    assert RateLimitBucket.objects.count() == 3

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta
from datetime import timezone as datetime_timezone

from django.db import IntegrityError, transaction
from django.utils import timezone
from ninja.throttling import SimpleRateThrottle

from core.models import RateLimitBucket


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    retry_after: float


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def consume_rate_limit(
    *,
    scope: str,
    identity: str,
    limit: int,
    window_seconds: int,
    now: datetime | None = None,
) -> RateLimitResult:
    """Atomically consume one request from a fixed-window Postgres bucket."""
    now = now or timezone.now()
    window_epoch = int(now.timestamp()) // window_seconds * window_seconds
    window_started_at = datetime.fromtimestamp(window_epoch, tz=datetime_timezone.utc)
    expires_at = window_started_at + timedelta(seconds=window_seconds)
    if limit <= 0:
        return RateLimitResult(False, max((expires_at - now).total_seconds(), 0))
    identity_hash = _hash(identity)
    key_hash = _hash(f"{scope}:{identity_hash}:{window_epoch}")

    with transaction.atomic():
        try:
            bucket = RateLimitBucket.objects.select_for_update().get(pk=key_hash)
        except RateLimitBucket.DoesNotExist:
            try:
                # The savepoint keeps a concurrent insert from breaking the outer
                # transaction before we lock and inspect the winning row.
                with transaction.atomic():
                    RateLimitBucket.objects.create(
                        key_hash=key_hash,
                        scope=scope,
                        identity_hash=identity_hash,
                        window_started_at=window_started_at,
                        expires_at=expires_at,
                    )
                return RateLimitResult(True, 0)
            except IntegrityError:
                bucket = RateLimitBucket.objects.select_for_update().get(pk=key_hash)

        retry_after = max((bucket.expires_at - now).total_seconds(), 0)
        if bucket.request_count >= limit:
            return RateLimitResult(False, retry_after)

        bucket.request_count += 1
        bucket.save(update_fields=["request_count"])
        return RateLimitResult(True, 0)


class PostgresRateThrottle(SimpleRateThrottle):
    """Ninja throttle backed by an atomic database counter, not a cache."""

    cache_format = "throttle_%(scope)s_%(ident)s"

    def __init__(self, rate=None):
        super().__init__(rate)
        self._retry_after = None

    def get_identity(self, request) -> str:
        if request.user and request.user.is_authenticated:
            return f"user:{request.user.pk}"
        return f"ip:{self.get_ident(request) or 'unknown'}"

    def get_cache_key(self, request):
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_identity(request),
        }

    def allow_request(self, request, view=None):
        if self.rate is None or self.num_requests is None or self.duration is None:
            return True
        key = self.get_cache_key(request)
        if key is None:
            return True
        result = consume_rate_limit(
            scope=str(self.scope),
            identity=key,
            limit=self.num_requests,
            window_seconds=self.duration,
        )
        self._retry_after = result.retry_after or None
        return result.allowed

    def wait(self):
        return self._retry_after


class PostgresAnonRateThrottle(PostgresRateThrottle):
    def get_cache_key(self, request):
        if getattr(request, "auth", None) is not None:
            return None
        return self.cache_format % {
            "scope": self.scope,
            "ident": f"ip:{self.get_ident(request) or 'unknown'}",
        }

from django.conf import settings
from django.db import models


class IdempotencyRecord(models.Model):
    identity_hash = models.CharField(max_length=64, primary_key=True)
    request_fingerprint = models.CharField(max_length=64)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    method = models.CharField(max_length=10)
    path = models.TextField()
    status_code = models.PositiveSmallIntegerField()
    response_data = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField()
    expires_at = models.DateTimeField(db_index=True)

    def __str__(self) -> str:
        return f"{self.method} {self.path} ({self.status_code})"


class RateLimitBucket(models.Model):
    """A durable, fixed-window API rate-limit counter."""

    key_hash = models.CharField(max_length=64, primary_key=True)
    scope = models.CharField(max_length=64)
    identity_hash = models.CharField(max_length=64)
    window_started_at = models.DateTimeField()
    expires_at = models.DateTimeField(db_index=True)
    request_count = models.PositiveIntegerField(default=1)

    def __str__(self) -> str:
        return f"{self.scope} ({self.request_count})"

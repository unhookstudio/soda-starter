from django.contrib import admin

from core.models import IdempotencyRecord, RateLimitBucket


@admin.register(IdempotencyRecord)
class IdempotencyRecordAdmin(admin.ModelAdmin):
    list_display = (
        "identity_hash",
        "user",
        "method",
        "path",
        "status_code",
        "completed_at",
        "expires_at",
    )
    search_fields = ("identity_hash", "user__email", "path")
    list_filter = ("method", "status_code", "completed_at", "expires_at")
    readonly_fields = (
        "identity_hash",
        "request_fingerprint",
        "user",
        "method",
        "path",
        "status_code",
        "response_data",
        "created_at",
        "completed_at",
        "expires_at",
    )

    def has_add_permission(self, request):
        return False


@admin.register(RateLimitBucket)
class RateLimitBucketAdmin(admin.ModelAdmin):
    list_display = (
        "scope",
        "request_count",
        "window_started_at",
        "expires_at",
    )
    search_fields = ("scope", "identity_hash", "key_hash")
    list_filter = ("scope", "window_started_at", "expires_at")
    readonly_fields = (
        "key_hash",
        "scope",
        "identity_hash",
        "window_started_at",
        "expires_at",
        "request_count",
    )

    def has_add_permission(self, request):
        return False

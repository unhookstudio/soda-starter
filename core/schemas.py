from datetime import datetime

from ninja import Schema


class DetailResponse(Schema):
    detail: str


class AvatarUrlsOut(Schema):
    small: str
    large: str
    expires_at: datetime

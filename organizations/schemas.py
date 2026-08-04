from datetime import datetime
from uuid import UUID

from ninja import Schema
from pydantic import ConfigDict


class WorkspaceOut(Schema):
    id: UUID
    name: str
    slug: str
    kind: str
    role: str
    creator_id: UUID | None
    created_at: datetime
    updated_at: datetime


class CurrentWorkspaceIn(Schema):
    workspace_id: UUID
    model_config = ConfigDict(extra="forbid")

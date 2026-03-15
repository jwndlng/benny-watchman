"""Request body for POST /investigate."""

from datetime import datetime
from pydantic import BaseModel


class InvestigateRequest(BaseModel):
    id: str
    type: str
    title: str
    description: str
    severity: str
    source: str
    timestamp: datetime
    raw: dict = {}

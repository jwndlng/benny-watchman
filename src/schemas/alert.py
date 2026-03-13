"""Incoming alert structure from the REST API."""

from datetime import datetime
from pydantic import BaseModel


class Alert(BaseModel):
    id: str
    type: str
    title: str
    description: str
    severity: str
    source: str
    timestamp: datetime
    raw: dict = {}

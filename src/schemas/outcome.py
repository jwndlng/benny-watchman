"""Outcome — the domain-agnostic summary of an investigation.

Every module maps its own verdict/severity onto this common shape so
investigations can be listed and compared across domains (SIEM, VM, …)
without deserializing their domain-specific report payloads.
"""

from pydantic import BaseModel, Field


class Outcome(BaseModel):
    """Cross-domain summary of an investigation's result."""

    disposition: str = Field(description="Domain verdict mapped to a common label (e.g. true_positive, exploitable)")
    priority: str = Field(description="Severity/priority mapped to a common label (e.g. high, P1)")

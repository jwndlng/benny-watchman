"""Shared horizontal capabilities injected into analyst modules.

Built once at the composition root and passed to a module's `investigate()`.
Holds configured instances only — no domain logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.capabilities.subagents.data.base_data_agent import BaseDataAgent
    from src.capabilities.tools.identity.assessment import IdentityTool


@dataclass
class Capabilities:
    """Typed container of the horizontal capabilities a module may consult."""

    data: dict[str, BaseDataAgent] = field(default_factory=dict)
    identity: IdentityTool | None = None

"""Abstract base for specialized data retrieval agents.

Each concrete subclass owns one backend (SQLite, Elasticsearch, ClickHouse, etc.),
declares a human-readable name and routing description, and exposes a run() method
the AnalystAgent calls via a dynamically registered tool.
"""

from abc import abstractmethod

from pydantic import BaseModel, Field
from pydantic_ai import AgentRunResult

from src.agents.base_agent import BaseAgent


class DataModel(BaseModel):
    """Structured result returned by any DataAgent run."""

    rows: list[dict[str, object]] = Field(
        description="Rows retrieved matching the request"
    )
    notes: str = Field(description="What was queried and any relevant context")


class BaseDataAgent(BaseAgent[DataModel]):
    """Base class for all data retrieval agents.

    Subclasses must:
      - Set self._name and self._routing_description before calling super().__init__()
        (because BaseAgent.__init__ reads self.instructions which may need them)
      - Implement initialize() to build self._routing_description from backend introspection
      - Implement the instructions property
    """

    _name: str
    _routing_description: str | None

    @property
    def name(self) -> str:
        """Data domain name — used as the tool name suffix (query_{name})."""
        return self._name

    @property
    def routing_description(self) -> str:
        """Compact summary of this source's tables, fields, and sample events.

        Injected as the tool docstring seen by AnalystAgent.
        Raises RuntimeError if initialize() has not been called.
        """
        if self._routing_description is None:
            raise RuntimeError(
                f"DataAgent '{self._name}' has not been initialized. "
                "Call await agent.initialize() before use."
            )
        return self._routing_description

    @abstractmethod
    async def initialize(self) -> None:
        """Introspect the backend and build routing_description.

        Called once at server startup. Raises on connection failure so that
        unreachable backends are detected before the first investigation.
        """

    async def run(  # type: ignore[override]
        self, prompt: str, **kwargs
    ) -> AgentRunResult[DataModel]:
        """Run the data agent, guarding against uninitialized state."""
        if self._routing_description is None:
            raise RuntimeError(
                f"DataAgent '{self._name}' has not been initialized. "
                "Call await agent.initialize() before use."
            )
        return await super().run(prompt, **kwargs)

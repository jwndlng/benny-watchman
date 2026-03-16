"""Base wrapper around pydantic_ai.Agent — all agents extend this."""

from pydantic_ai import Agent
from pydantic_ai.models import Model


class BaseAgent[TOutput]:
    def __init__(
        self, model: str | Model, output_type: type[TOutput], instructions: str
    ) -> None:
        self.instructions = instructions
        self.agent: Agent[None, TOutput] = Agent(
            model=model,
            output_type=output_type,
            system_prompt=instructions,
        )

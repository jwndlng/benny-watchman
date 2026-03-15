"""Base wrapper around pydantic_ai.Agent — all agents extend this."""

from pydantic_ai import Agent


class BaseAgent[TOutput]:
    def __init__(
        self, model: str, output_type: type[TOutput], instructions: str
    ) -> None:
        self.agent: Agent[None, TOutput] = Agent(
            model=model,
            result_type=output_type,
            system_prompt=instructions,
        )

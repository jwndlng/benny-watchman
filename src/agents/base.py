"""Base wrapper around pydantic_ai.Agent — all agents extend this."""

from pydantic_ai import Agent


class BaseAgent[TDeps, TOutput]:

    def __init__(self, model: str, output_type: type[TOutput], instructions: str) -> None:
        self.agent: Agent[TDeps, TOutput] = Agent(
            model=model,
            result_type=output_type,
            system_prompt=instructions,
        )

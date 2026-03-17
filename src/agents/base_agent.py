"""Base wrapper around pydantic_ai.Agent — all agents extend this."""

import logfire
from pydantic_ai import Agent, AgentRunResult
from pydantic_ai.models import Model
from pydantic_ai.usage import UsageLimits

from src.config import config


class BaseAgent[TOutput]:
    @property
    def instructions(self) -> str:
        raise NotImplementedError

    @property
    def constraints(self) -> list[str]:
        return []

    @property
    def system_prompt(self) -> str:
        prompt = self.instructions
        if self.constraints:
            items = "\n".join(f"- {c}" for c in self.constraints)
            prompt += f"\n\nBe aware of your constraints:\n{items}"
        return prompt

    def __init__(
        self,
        model: str | Model,
        output_type: type[TOutput],
        name: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self._usage_limits = UsageLimits(request_limit=config.agent.max_requests)
        self.agent: Agent[None, TOutput] = Agent(
            model=model,
            name=name,
            model_settings={"api_key": api_key} if api_key else None,
            output_type=output_type,
            system_prompt=self.system_prompt,
        )

    def run_sync(self, prompt: str, **kwargs) -> AgentRunResult[TOutput]:
        result = self.agent.run_sync(prompt, usage_limits=self._usage_limits, **kwargs)
        u = result.usage()
        logfire.info(
            "{agent} usage",
            agent=self.agent.name,
            requests=u.requests,
            input_tokens=u.input_tokens,
            output_tokens=u.output_tokens,
        )
        return result

    async def run(self, prompt: str, **kwargs) -> AgentRunResult[TOutput]:
        result = await self.agent.run(prompt, usage_limits=self._usage_limits, **kwargs)
        u = result.usage()
        logfire.info(
            "{agent} usage",
            agent=self.agent.name,
            requests=u.requests,
            input_tokens=u.input_tokens,
            output_tokens=u.output_tokens,
        )
        return result

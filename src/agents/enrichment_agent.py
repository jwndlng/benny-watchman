"""Enriches indicators of compromise with external threat intelligence.

Receives enrichment requests from the AnalystAgent (IPs, domains, hashes, URLs).
Owns all external API integrations: VirusTotal, IDP lookups, web lookups.
Adding a new intel provider means adding a tool here only.
"""

from pydantic import BaseModel, Field

from src.agents.base_agent import BaseAgent


class EnrichmentModel(BaseModel):
    enrichments: dict[str, dict] = Field(
        description="Enrichment data keyed by indicator"
    )


class EnrichmentAgent(BaseAgent[EnrichmentModel]):
    @property
    def instructions(self) -> str:
        return (
            "You are a threat intelligence expert. Enrich indicators of compromise "
            "(IPs, domains, hashes, URLs) using available tools and return structured findings."
        )

    def __init__(self, model: str) -> None:
        super().__init__(
            model=model, output_type=EnrichmentModel, name="EnrichmentAgent"
        )

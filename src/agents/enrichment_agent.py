"""Enriches indicators of compromise with external threat intelligence.

Receives enrichment requests from the AnalystAgent (IPs, domains, hashes, URLs).
Owns all external API integrations: VirusTotal, IDP lookups, web lookups.
Adding a new intel provider means adding a tool here only.
"""

from pydantic import BaseModel, Field

from src.agents.base import BaseAgent


class EnrichmentModel(BaseModel):
    indicators: list[str] = Field(description="IPs, domains, hashes, or URLs to enrich")


class EnrichmentResult(BaseModel):
    enrichments: dict[str, dict] = Field(
        description="Enrichment data keyed by indicator"
    )


class EnrichmentAgent(BaseAgent[EnrichmentModel, EnrichmentResult]):

    def __init__(self, model: str, instructions: str) -> None:
        super().__init__(
            model=model, output_type=EnrichmentResult, instructions=instructions
        )

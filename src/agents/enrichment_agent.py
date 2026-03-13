"""Enriches indicators of compromise with external threat intelligence.

Receives enrichment requests from the AnalystAgent (IPs, domains, hashes, URLs).
Owns all external API integrations: VirusTotal, IDP lookups, web lookups.
Adding a new intel provider means adding a tool here only.
"""


class EnrichmentAgent:
    pass

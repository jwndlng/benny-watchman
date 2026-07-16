"""Vulnerability threat-intel enrichment — a VM-owned composite tool (dev stub).

Enrichment sources are vertical (VM uses CVE/EPSS/KEV; SIEM uses IOC intel), so
this is owned by the VM module rather than being a shared horizontal capability.
It is a composite deterministic tool per the compression-boundary rule — real
CVE/EPSS/KEV API clients are a follow-up.
"""

from __future__ import annotations


class VulnIntelCapability:
    """Composite CVE/EPSS/KEV enrichment. Dev stub — real API clients deferred."""

    async def enrich(self, cve: str) -> dict[str, object]:
        """Return threat-intel context for a CVE (EPSS score, KEV membership, …).

        Stub implementation returning placeholder context; real intel clients are
        a follow-up change.
        """
        return {
            "cve": cve,
            "epss": None,
            "kev": False,
            "note": "enrichment stub — real CVE/EPSS/KEV intel deferred",
        }

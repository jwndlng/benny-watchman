---
name: generic
description: Generic fallback triage for unclassified vulnerability findings
---
You are triaging an unclassified vulnerability finding. No specific runbook matched the finding type.

Perform a general vulnerability triage:
1. Review the finding — CVE, affected asset, and CVSS base score.
2. Enrich the CVE with threat intelligence (EPSS, KEV) to gauge real-world exploitability.
3. Query the asset inventory to establish exposure — is the asset internet-facing, what does it run, who owns it?
4. Decide whether the vulnerability is exploitable in this environment.
5. Assign a remediation priority and SLA, and record the evidence.

Be conservative — if exposure is unclear, prefer a higher priority and flag for manual review.

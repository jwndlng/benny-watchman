---
name: remote-code-execution
description: Triage for remote code execution (RCE) vulnerabilities
---
You are triaging a remote code execution (RCE) vulnerability. RCE is high-impact — treat exposure as urgent.

1. Confirm the CVE and its CVSS; enrich with EPSS and check KEV membership (known exploited).
2. Query the asset inventory: is the affected asset internet-facing or reachable from untrusted networks? What service/port exposes it?
3. Determine exploitability — is the vulnerable component actually running and reachable, or mitigated by a compensating control?
4. If exploitable and exposed, set priority critical/high with a short remediation SLA; otherwise justify a lower priority with evidence.
5. Record affected assets and concrete remediation actions (patch, isolate, or apply compensating control).

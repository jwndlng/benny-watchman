# Brainstorming

This document is used to gather on ideas, which are not refined yet. Once refined they may go into the [design](DESIGN.md).


## Skills

### Type of Skills
Skills are essential for the model to acquire special knowledge depending on the context. In terms of a SOC analyst these can go into the following directions:

1. Playbook Skills per Detection Rules
2. External Look up Skills e.g. Vulnerability Database, Known Hacker Pages
3. Investigation/Database Review Skills e.g. Explaining how to investigate with the current datalake

### Chain of Skills

Explore how efficiently it is to chain skills especially for playbooks. Lets imagine we have the following approach:

```
Analyze Alert ------> Loads Generic Runbook (basic instructions) ----> Loads specific alert runbook ----> Loads MITRE tactic ------> Loads technique A
                                                                                                                             ------> Loads technique B
                                                                                                                             ------> Loads technique C
```

### Skill Engine Loader

If this project will be used in a broader context and given it really relies on Skills, not every deployment requires all skills.
So the approach can be either 1) let the agent decide what skill to load or 2) we don't load all skills by default.

Having a Skill Engine Loader can provide the following advantages:

1. Load skills based on context e.g. Clickhouse Skills if clickhouse is used as datalake or Elastic if we built on a Elastic SIEM
2. Benchmarking: load only specific skills to test in a isolated environment
3. Integration testing

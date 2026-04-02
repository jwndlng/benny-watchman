---
name: sync-skill
description: Automatically symlinks skills into workflows, claude, and gemini directories.
---

# Sync Skills

This skill maintains synchronization between your manually created skills and the various AI-agent configuration directories. 

It symlinks everything from `.agent/skills/` into:
- `.agent/workflows/`
- `.claude/skills/`
- `.gemini/skills/`

It automatically ignores `openspec-*` skills, as those are managed by the OpenSpec CLI.

## How to execute

Run the underlying synchronization script whenever you add or remove non-openspec skills:
```bash
bash .agent/skills/sync-skill/scripts/sync.sh
```

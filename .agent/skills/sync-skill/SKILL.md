---
name: sync-skill
description: Automatically syncs local skills to claude, gemini (via symlinks), and workflows (via copied markdown files).
---

# Sync Skills

This skill maintains synchronization between your manually created skills and the various AI-agent configuration directories. 

For each skill in `.agent/skills/`, it performs the following:
- **Claude & Gemini**: Creates a directory symlink in `.claude/skills/` and `.gemini/skills/`.
- **Workflows**: Copies the `SKILL.md` file directly into `.agent/workflows/` and renames it to `<skill-name>.md`.

It automatically ignores `openspec-*` skills, as those are managed by the OpenSpec CLI.

## How to execute

Run the underlying synchronization script whenever you add or remove non-openspec skills:
```bash
bash .agent/skills/sync-skill/scripts/sync.sh
```

#!/usr/bin/env bash
set -e

ROOT_DIR=$(git rev-parse --show-toplevel 2>/dev/null || pwd)

SKILLS_DIR="$ROOT_DIR/.agent/skills"
WORKFLOWS_DIR="$ROOT_DIR/.agent/workflows"
CLAUDE_DIR="$ROOT_DIR/.claude/skills"
GEMINI_DIR="$ROOT_DIR/.gemini/skills"

mkdir -p "$WORKFLOWS_DIR" "$CLAUDE_DIR" "$GEMINI_DIR"

echo "Syncing skills from $SKILLS_DIR..."

for skill_path in "$SKILLS_DIR"/*; do
  if [ -d "$skill_path" ]; then
    skill_name=$(basename "$skill_path")
    
    if [[ "$skill_name" == openspec-* ]]; then
      echo "Skipping $skill_name (managed by openspec CLI)"
      continue
    fi
    
    echo " -> $skill_name"
    
    # Create symlinks for Claude and Gemini
    ln -sfn "../../.agent/skills/$skill_name" "$CLAUDE_DIR/$skill_name"
    ln -sfn "../../.agent/skills/$skill_name" "$GEMINI_DIR/$skill_name"
    
    # Copy SKILL.md to workflows with the new name
    if [ -f "$skill_path/SKILL.md" ]; then
      cp "$skill_path/SKILL.md" "$WORKFLOWS_DIR/${skill_name}.md"
    fi
  fi
done

echo "Sync complete!"

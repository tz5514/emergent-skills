---
name: extract-transcript
description: Extract a Claude Code, Cursor, or Codex session transcript into a compact, category-selective JSONL artifact for review or analysis.
---

# Extract Transcript

```bash
python3 {skill_dir}/scripts/extract_transcript.py [transcript.jsonl] \
  [--content-category CATEGORY]... \
  [--include-launched-agents]
```

Omit the path to extract the current session. `--include-launched-agents`
also exports launched agents, recursively, each as its own JSONL artifact.

## Category selection

Without `--content-category`, the artifact keeps user prompts, user-visible
agent output, and interactive question tool calls with their recorded answers.
Any `--content-category` replaces that default with exactly the categories
named (repeat the flag to combine):

- `user_prompt`
- `user_visible_agent_output`
- `reasoning`
- `tool_activity`
- `agent_instructions`
- `turn_lifecycle`

## Result

Success prints the artifact directory and the primary `transcript.jsonl` path
on stdout; the directory also holds extracted images under `assets/` and an
`extraction-manifest.json` integrity manifest. A stderr `Extraction
conditions:` report names anything omitted or uncertain — surface it alongside
the result. A non-zero exit delivered no artifact.

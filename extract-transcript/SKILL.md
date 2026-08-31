---
name: extract-transcript
description: Extract a Claude Code, Cursor, or Codex session transcript into a compact, category-selective JSONL artifact for review or analysis.
---

# Extract Transcript

```bash
python3 {skill_dir}/scripts/extract_transcript.py transcript.jsonl \
  [--current-session] \
  [--content-category CATEGORY]... \
  [--include-launched-agents]
```

The transcript path is required. When the user named no transcript, first use
the `transcript-path` skill to get the current session's transcript path, then
pass that path with `--current-session`, which stops the artifact before this
extraction request. `--include-launched-agents` also exports launched agents,
recursively, each as its own JSONL artifact.

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

If the script succeeds but stderr reports unrecognized records, relay that
sentence to the user verbatim; no other action is needed.

If the script exits non-zero, analyze the raw transcript yourself and
hand-produce an artifact in the same output format, clearly labeled as
LLM-fallback output with no mechanical-fidelity guarantee.

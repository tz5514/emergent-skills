---
name: transcript-path
description: Print the absolute path of the current agent session's transcript file, for the runtime it runs in (Claude Code / Codex / Cursor). Use when the user wants the current session's transcript path.
---

# Transcript Path

Run:

```bash
python3 {skill_dir}/scripts/main.py
```

Reply with the script's stdout — the path line alone is the complete answer. If it exits non-zero, report that the current session's transcript could not be resolved.

Runtime detection and per-runtime resolution live in `scripts/`; read them only when changing the skill itself.

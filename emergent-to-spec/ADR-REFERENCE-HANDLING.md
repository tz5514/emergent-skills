# Related ADR handling

1. **Select.** From the conversation alone — no user interview, no ADR-directory enumeration — account for every ADR the conversation mentions:
   - `draft_entries`: every draft ADR this spec will implement; drafts outside this spec's implementation stay out.
   - `active_entries`: only active ADRs whose constraints are not obvious from the codebase — reference-only, no lifecycle writes.
   - Archived ADRs stay out.

   Each entry carries `number`, a repository-root-relative `path`, and a caller-supplied `bounded_context` (never inferred from the path); active entries may add `relevance_note`.

2. **Validate.** With `entries = [*draft_entries, *active_entries]` and the explicit repository root, call [`check_path_existence(entries, repo_root)`](scripts/path_existence_check.py). Repair each missing entry yourself — locate the file from the entry's own `number` and `path`, correct that entry, never add entries or ask the user — and re-check until `all_present`.

3. **Render.** Call [`render_adr_reference_blocks(draft_entries, active_entries, spec_bounded_context)`](scripts/adr_reference_block.py) — even with empty lists — and append its non-empty output verbatim at the very end of the spec; never hand-write the headings or rows. Two empty lists return the exact empty string, meaning nothing to append.

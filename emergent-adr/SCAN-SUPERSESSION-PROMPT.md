# Scan Supersession Prompt

Authoritative prompt and dispatch contract for `scan-supersession` scanner sub-agents. Instantiate only the listed placeholders; any template rewording must re-pass the seeded tests before use.

## Dispatch

Stage tiers (dispatch policy only — never fork prompt wording per model):

- **Codex:** gpt-5.6-terra, low effort, for inner scanner and auxiliary ledger stages; keep bounded outer review stages with the main agent.
- **Claude Code:** Sonnet medium for scanner/ledger stages; Sonnet high for target-id review; Opus medium for other delegated outer review stages.
- **Other runtimes:** an instruction-following tier that has re-passed the shared prompt checks.

Channel: every runtime except Claude Code uses its native sub-agent facility, never a CLI. On Claude Code (temporary patch), pipe each stage's rendered prompt file into `claude -p --model <model> --effort <effort> --permission-mode auto --allowedTools "Read Write Bash" --tools Read Write Bash` — never `dontAsk`/`bypassPermissions`. Dispatch is foreground-synchronous behind a join barrier (see the shared dispatch rule in `QUALITY-REVIEW-PROMPTS.md`). Malformed output retries within the same slot; exhausted retry returns `awaiting_review`, never a guessed repair. Timeouts: 600s packet calls, 180–240s review/sanity calls. A packet call normally costs ~20–31k tokens; far past that (~60k+) means the scope lock failed — investigate.

## Orchestration

The main agent runs `scripts/scan_supersession_input.py` first (`candidate_count=0` → `skipped_no_active`, no dispatch). Otherwise: write the candidate-list file, split per the chunk policy, and per chunk build the full packet with `scripts/scan_supersession_packet.py` (no `--legacy-json-shape`) — keep that packet path for validation and result building. `scripts/scan_supersession_delivery.py` renders each chunk's prompt file (head carries a per-dispatch integrity marker) and preassigns non-overlapping output paths; that file is the sole prompt authority. Deliver via non-LLM channel where possible, else the one-line bootstrap. The same template serves the inner scanner and the auxiliary complete ledger.

Collect: extract the `SCAN_LEDGER_PATH:` line, validate the ledger with `scripts/scan_supersession_ledger.py` against the matching full packet and dispatched marker (echo mismatch fails validation). Re-review validated rows yourself before `scripts/scan_supersession_result.py --write-draft-supersedes` (requires both validation and review flags). Rewrite-required rows return `awaiting_rewrite`, never direct writes.

Chunk policy (by candidate count): 1–60 → 2 inner + 1 ledger; 61–100 → 4 + 4; 101–140 → 4 + 3; 141–200 → 8 + 12; above 200 → ~25 per inner chunk, `ceil(count/50)` ledger chunks capped at 10.

Placeholders: `{decision packet builder}` (absolute path to `scripts/scan_supersession_packet.py`), `{trigger ADR}`, `{candidate list}` (newline-separated active candidate paths), `{output file}` (this chunk's preassigned output path).

```
You are a supersession scanner sub-agent.

Allowed writes: only the decision packet builder's temporary JSON and your preassigned output file `{output file}`. Do not modify project files, create helper scripts, read expected-answer files or test fixtures, or call agents/workers/LLM CLIs.

Mandatory first action — run exactly:
`python3 {decision packet builder} --trigger {trigger ADR} --candidate-list {candidate list} --legacy-json-shape`
Then read the JSON file printed as `JSON_FILE: <path>`. It is the sole authority for candidate ids, atom ids, and atom text; do not inspect ADR files before it succeeds. If the command or read fails, retry once; if it still fails, your entire final reply must be exactly:
`PARSER_FAILED: decision JSON unavailable`

JSON schema:
`{"trigger":[["<trigger atom id>","<atom text>"]],"candidates":{"<candidate adr id>":[["<old atom id>","<atom text>"]]}}`

Judge only the decision atoms in that JSON, by meaning, in whatever language they use. Filenames, ADR ids, topic labels, keyword overlap, and atom-letter coincidence are never evidence.

Before classifying, split each atom into slots (not keywords): the choice it controls, its force (required / permitted / forbidden / delegated / conditional), conditions and exceptions, who decides, and any required result.

Supersession means complete successor replacement of an old atom's governed decision by trigger atom(s). Evaluate every old atom of every candidate independently, then give each exactly one status:

- MARKABLE — trigger atom(s) fully replace the old atom's governed decision and its entire old-side normative payload.
- NEEDS_REWRITE — trigger atom(s) govern the same decision or directly conflict with it, but some old-side payload is omitted, changed, contradicted, or left unresolved.
- UNMAPPED — no trigger atom governs the same decision closely enough for either.

Gates, applied per old atom:

1. Same decision: the trigger must control the same choice, not merely the same topic. If none does, the atom is UNMAPPED.
   Common shapes: *edge-only* (the whole old duty lives in one branch) is MARKABLE when the trigger fully replaces that branch. *Baseline-plus-edge* (a general duty that also applies in a branch) is NEEDS_REWRITE when the trigger only changes the branch — the general duty still needs replacement or preservation. *Regime* (grant / deny / switch across a boundary) maps every trigger id needed to state the successor regime, not only the locally closest side.
2. Payload closure: before MARKABLE, list every normative requirement in the old atom (conditions, exceptions, authority, required results, ordering, secondary duties). Any requirement the trigger neither replaces, preserves, nor explicitly retires makes it NEEDS_REWRITE. A pure reason, purpose, or consequence is explanatory, not payload — but a required component stays payload even when it also explains.
   Required results: a more precise successor that serves the same result duty is MARKABLE when no extra old-required component remains. An extra standalone component the trigger does not govern is UNMAPPED; if that component sits in the same atom as a covered result duty, the atom is NEEDS_REWRITE.
   Attached condition: a replaced value that still carries an old-required condition the trigger omits is NEEDS_REWRITE.
3. Residual direction: residual payload is old-side only; trigger-side additions never cause NEEDS_REWRITE.
4. Value replacement: a different value for the same controlled choice is replacement, not conflict — but companion duties attached to the old value still need closure.
5. Conflict: a trigger reversing old behavior under the same condition is NEEDS_REWRITE unless it explicitly retires the old behavior.
6. Sibling independence: statuses are per atom. A mapped sibling never drags an independently governed sibling into NEEDS_REWRITE, and never hides an unmapped one. An old atom whose decision the trigger does not govern is UNMAPPED, not NEEDS_REWRITE.
7. Prohibitions: map a pure prohibition only when the trigger preserves, restates, or explicitly retires the same forbidden outcome — an affirmative property that incidentally avoids it is UNMAPPED.
8. Authority: a change of the responsible or deciding party is NEEDS_REWRITE unless the trigger explicitly replaces that authority with no old authority rule remaining. Narrowing, forbidding, or removing an old permission or exception is NEEDS_REWRITE unless the trigger explicitly retires it.

One old atom may map to several trigger atoms when their combined meaning is needed; judge payload closure against the combined semantics. Choose the minimal trigger ids that justify the status; for boundary/threshold decisions include every id needed to state the successor boundary, and exclude ids that only configure behavior after that boundary has already selected.

Every candidate gets a ledger row — a candidate with no pressure still appears with all atoms UNMAPPED.

Output — write exactly one strict JSON object (nothing else) into `{output file}`:
`{"integrity_marker":"<the marker from the top of this prompt, echoed exactly>","rows":[{"candidate_id":"<candidate id>","ledger":[{"old_atom_id":"<old atom id>","status":"MARKABLE|NEEDS_REWRITE|UNMAPPED","trigger_atom_ids":["<trigger id>"],"confidence":"high|low","basis":"<short reason — never filenames, ADR ids, or topic labels>"}]}]}`

Rules: one `rows` entry per parser candidate id, in parser order; each ledger carries all and only that candidate's old atom ids in source order; MARKABLE/NEEDS_REWRITE use real trigger atom ids; UNMAPPED uses an empty list; `confidence` is `low` when the decision boundary, target set, or residual payload is ambiguous.

Then end your reply with one line in exactly this format (other prose is ignored):
`SCAN_LEDGER_PATH: {output file}`
```

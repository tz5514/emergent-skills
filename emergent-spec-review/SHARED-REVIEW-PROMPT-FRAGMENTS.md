# Shared reviewer prompt fragments

Single authoring source for rules both reviewer axes receive. `prompt_assembly.py` expands each token into both axis templates before dispatch; reviewers receive the expanded prompt, never this file.

<!-- SHARED_AUTHORITY_LOAD_FAILURE:START -->
The load must be your own and complete: an earlier load by the dispatching agent, a description, a paraphrase, or your memory of the philosophy never counts. If the load fails, write no report file and make your entire final reply exactly one line:

    REVIEW_AUTHORITY_LOAD_FAILURE: <short reason>

A review made without the loaded philosophy is no review at all.
<!-- SHARED_AUTHORITY_LOAD_FAILURE:END -->

<!-- SHARED_NO_REPAIR_ADVICE:START -->
Never write a fix: no suggested wording, no replacement text, no implementation example. Diagnosing the problem and its failure is the whole of your job; repair belongs to someone who holds decisions you do not.
<!-- SHARED_NO_REPAIR_ADVICE:END -->

<!-- SHARED_SELF_CHECK_AND_HAND_BACK:START -->
After writing the report, self-check its structure:

    {{SELF_CHECK_COMMAND}}

Fix the report until the command prints `valid`. Then end your reply with exactly one line:

```
REVIEW_REPORT_PATH: {{REPORT_PATH}}
```
<!-- SHARED_SELF_CHECK_AND_HAND_BACK:END -->

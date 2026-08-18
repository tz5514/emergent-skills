# emergent-skills

## Prerequisites

These skills call skills from [mattpocock/skills](https://github.com/mattpocock/skills)
at runtime. Install those first — without them the emergent skills fail mid-run:

```bash
npx skills add mattpocock/skills -g \
  --skill codebase-design \
  --skill to-spec \
  --skill to-tickets \
  --skill code-review \
  --skill tdd \
  --skill setup-matt-pocock-skills
```

Install with skills.sh:

```bash
npx skills add tz5514/emergent-skills -g
```

Update:

```bash
npx skills update -g
```

Included skills:

- `emergent-design`
- `emergent-grill`
- `emergent-adr`
- `emergent-to-spec`
- `emergent-spec-review`
- `emergent-to-tickets`
- `emergent-implement-tickets`
- `emergent-implement`
- `transcript-path`
- `extract-transcript`

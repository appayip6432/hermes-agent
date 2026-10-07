---
title: "Alignment Synthesis"
description: "Review evidence-backed personal-agent guidance without changing ongoing conversations"
---

# Alignment synthesis

Alignment synthesis is a small, optional personal-agent prompt layer. It distills
reviewed successes and corrections into five bounded principles: compress wording
without losing substance, distinguish sharing from tasks, protect attention,
minimize disclosure, and carry supported corrections forward. It is separate from
memory facts, tasks, deadlines, skills, and permissions.

The default is **shadow**: the explicit generation command creates a reviewable
artifact but never injects it. Nothing scans your conversations, memories, files,
or external services automatically. Generation is deterministic and offline; it
selects catalog principles from your annotated evidence, rather than asking a
model to invent preferences. There is no new model tool, cron job, or provider call.

## Generate and review

Run from an activated Hermes checkout. Artifacts default to the active profile's
`alignment/` directory, resolved through `get_hermes_home()`. An explicit
`--store DIRECTORY` before the subcommand uses a separate review sandbox.

```bash
python -m agent.alignment_synthesis catalog
python -m agent.alignment_synthesis template > reflection.json
# Edit reflection.json: replace the synthetic example with authorized evidence.
python -m agent.alignment_synthesis generate --input reflection.json
python -m agent.alignment_synthesis review VERSION
python -m agent.alignment_synthesis validate VERSION
python -m agent.alignment_synthesis approve VERSION --confirm-reviewed
```

`VERSION` is the full digest printed by `generate`. Review shows the compact prompt,
all source excerpts and reflections, and the parent diff. Approval records review
of that exact version; it does not enable injection or change configuration.
Review output contains the evidence you supplied, so choose where you display or
save it. Keep real evidence and generated artifacts out of source control.

Each reflection has an immutable `id`, a `rule` from `catalog`, an `outcome`, an
`effect`, a short `note`, and one or more exact `evidence` quotes with original
`ref` values. Sources contain only `ref`, `role`, and `content`. Use durable source
references, not a summary's identifier or an invented array position.

| Outcome | Effect | Evidence requirement |
| --- | --- | --- |
| `success` | `adopt` | Explicit user feedback supporting the principle |
| `correction` | `adopt` or `retire` | Explicit user correction supporting the change |
| `ambiguous` | `observe` | Original evidence of the uncertain outcome; never changes guidance |

An assistant's claim that something worked and the user's silence are not success
evidence. When feedback is missing, record the relevant assistant action as
`ambiguous` with `observe`. Do not invent a user response. At approval, verify that
the original source is authentic, the quote supports the interpretation, and its
scope is appropriate. Validation checks structure, bounds, role, and exact quote
matches **within the supplied evidence**; it cannot verify truth or semantic
support, and does not fetch references.

### Reuse existing memory evidence

If you already have an authorized direct-message export, `prepare` reuses the
memory checkpoint's direct-message filter. It excludes system/tool rows,
`_compressed_summary` rows, and assistant tool-call wrappers without prose. It
retains original durable `_row_id` references and rejects missing ids rather than
inventing them. It does not open the session database or read memory files.

```json
{
  "session_id": "example",
  "messages": [
    {"_row_id": 17, "role": "user", "content": "Keep the detail, but use fewer words."}
  ]
}
```

```bash
python -m agent.alignment_synthesis prepare --input authorized-export.json > reflection.json
# Add reflections; prepare intentionally makes no interpretation or approval.
python -m agent.alignment_synthesis generate --input reflection.json
```

Exports must preserve summary metadata. Text-only exports without durable ids are
not supported by this adapter; curated evidence may instead use the template's
source schema with genuine original references.

## Opt in for new conversations

After review, select the approved version through the ordinary profile settings:

```bash
hermes config set alignment_synthesis.version VERSION
hermes config set alignment_synthesis.mode active
```

Equivalent `config.yaml`:

```yaml
alignment_synthesis:
  mode: shadow  # shadow (default), off, or active
  version: ""  # Full reviewed digest; required for active injection
```

Only `active` with a valid snapshot and review receipt injects. `shadow`, `off`,
unknown modes, and unreviewed/missing/invalid artifacts inject nothing. Settings
and artifacts are scoped to the owning profile, including multiplexed agents.
The prompt contains fixed catalog prose and a version marker, never source
excerpts, source references, reflection notes, personal facts, or arbitrary
generated instructions.

The selection is frozen for the conversation, including compression, process
resume, and model changes. A legacy conversation without this layer keeps that
absence. Use a new conversation (`/new`) to adopt a changed selection; `/resume`
uses that session's original selection. Disabling or deleting artifacts also only
affects new conversations. Current requests and new supported corrections still
take precedence over the old advisory layer immediately.

## Corrections, versions, and bounds

Append new evidence/reflection ids and generate against the selected parent:

```bash
python -m agent.alignment_synthesis generate --input correction.json --parent OLD_VERSION
python -m agent.alignment_synthesis diff OLD_VERSION NEW_VERSION
python -m agent.alignment_synthesis review NEW_VERSION
python -m agent.alignment_synthesis approve NEW_VERSION --confirm-reviewed
hermes config set alignment_synthesis.version NEW_VERSION
```

Supply the source rows quoted by the new reflections. Parent evidence is retained;
existing ids/references cannot be rewritten. Reflections are evaluated in append
order, so a later supported correction can retire a previously adopted principle.
Ambiguity never retires or adopts one. The new version requires its own review.
Diffs include evidence-only changes even when the prompt is identical. To roll
back, select an earlier approved version for a new conversation.

Snapshots are content-addressed JSON under `alignment/versions/`; review receipts
live under `alignment/approved/`. Publication is atomic and does not overwrite a
different artifact. Validation rejects tampering, duplicate JSON keys, unknown
fields/rules, and unsupported schema versions. Digests detect corruption, not a
malicious writer with access to the same account; this is not an OS security boundary.

The policy body is capped at 1,800 characters, plus a small version frame. Evidence
is capped at 256,000 serialized bytes, 100 sources (8,000 characters each), and
100 reflections. A reflection permits eight quotes (1,000 characters each) and a
500-character note. JSON nesting is limited to 12 levels. Overflow is rejected,
never silently truncated. There is no automatic eviction or background
accumulation. At the evidence limit,
review a new bounded root bundle explicitly and retain prior snapshots for audit.

The catalog deliberately cannot encode arbitrary new preferences. Task-specific
procedures belong in skills; facts, tasks, and deadlines stay in their existing
stores. This feature supplies advisory language, not enforcement: it cannot grant
permission, override safety, or guarantee a model will follow a preference.

---
title: "Alignment Synthesis"
description: "Evidence-conditioned personal-agent reflection with reviewed startup guidance"
---

# Alignment synthesis

The nightly question is **what have these interactions taught me about being a better agent for this user?** It complements factual memory, skills and repair audits. It interprets successes, corrections and uncertainty into scoped patterns, registers, tensions, attention guidance, continuity and watchouts. It is not a factual backlog or permission store.

Default operation is **shadow**. Model generation never enables injection or changes scheduling. Only explicitly approved versions selected in configuration enter new conversations. Existing conversations retain their pinned presence or absence through rebuild, compression and resume.

## Nightly workflow (install later)

From an activated checkout, supply a bounded export with authorized original direct conversation evidence:

```json
{"schema":1,"window":"example-night","provenance":"synthetic labelled export","sources":[{"ref":"export:example:original-17","role":"user","content":"That concise answer kept the tradeoffs. Keep doing that."}]}
```

`ref` identifies the original message in its source, not an invented database row. Label supplied conversation excerpts as supplied, not DB-authenticated. Never export private/work material without explicit scope and permission. No DB collector or automatic global scan is included. Sources are user/assistant prose, not system/tool instructions or compressed summaries. The existing `prepare` adapter can filter a durable-row-ID session export; use its `sources` in the explicit window document. Exports and receipts stay out of source control.

```sh
python -m agent.alignment_synthesis --store REVIEW_DIR nightly --input WINDOW_EXPORT.json
python -m agent.alignment_synthesis --store REVIEW_DIR review VERSION
python -m agent.alignment_synthesis --store REVIEW_DIR diff OLD_VERSION VERSION
python -m agent.alignment_synthesis --store REVIEW_DIR approve VERSION --confirm-reviewed
```

`nightly` calls the actual Hermes auxiliary router (`call_llm(task="alignment")`), following the owning profile's `auxiliary.alignment` provider/model/reasoning settings and existing credential routing. Configure a route later using the ordinary Hermes settings interface; do not put credentials in YAML. Provider fees and outbound transfer to the configured model apply. The source payload is data, never worker instructions. Generation is schema-validated JSON, not a fixed five-rule selection.

After separate scheduling authorization, invoke this same command from a scheduler with an explicit per-profile `HERMES_HOME`, checkout/interpreter and prepared export path. Schedule export preparation separately with an authorized source scope. No cron is installed by this workflow. Repeating an identical content-addressed window returns its prior version without another model call or rewinding the head. Changed exports create distinct windows. This independent ledger never consumes canonical memory acknowledgment records. Failed validation/model calls do not advance a checkpoint or active selection. Prior versions remain readable.

Each new window automatically receives the last successful shadow snapshot as its parent, including its original evidence. The model emits additions rather than rewriting the whole history. Omitted older lessons remain. An explicit `revisions` entry names a `target` lesson, a new `replacement` correction, a contradiction `reason`, and remaining `uncertainty`. Only a correction backed by fresh user evidence can supersede a prior lesson; uncertainty and silence cannot retire one. The parent keeps the original interpretation for review. Reflection IDs remain reserved across the entire immutable parent chain, even after retirement; additions must use new IDs. Re-emitting an active or retired ID rejects the window without advancing the shadow head. Replacement guidance must preserve still-supported scope and exceptions; review must verify that semantic claim.

The worker serializes writers with `.worker-lock` and commits `head.json` by atomic replacement after publishing the snapshot and receipts. The head ledger is the commit authority, not the presence of a prepared file. Validation or I/O failure retains the previous successful head. Interrupted workers may leave orphan prepared artifacts and a stale lease; inspect retained receipts and verify that no worker remains before manually removing a stale lease. The head is a shadow cursor and never selects an active prompt or approves a version. Existing independent stores without a head start a new rolling chain; old versions remain available for review.

## Interpretation and review

Schema 2 reflections carry original exact citations, outcome (`success`, `correction`, `ambiguous`), kind (`explicit_preference`, `inference`), dimension, scope and expressive guidance. Uncertain outcomes only support qualified inference; silence is not approval. Quote matching checks provenance consistency, not authenticity or semantic entailment. Human review must check those separately and reject unsafe or unsupported guidance before approval.

The compact rendered section contains qualified interpretation rather than raw quotes or references. It explicitly yields to current instructions, corrections and safety; it grants no permission. A local model can still produce an unsafe interpretation: bounds and advisory wording are not semantic enforcement. Review is load-bearing.

Artifacts retain evidence/reflections and full successful model prompt/output receipts under `versions/`, `runs/`, `windows/`, and `approved/`. `attempts/` records requests before calls and failed raw model responses with exception types (exception text is omitted because provider exceptions can contain credentials). Version diffs include source changes. The prompt is at most 1,800 characters; input is at most 256,000 bytes, 100 sources of at most 8,000 characters, and eight active expressive reflections with four citations each. Rolling evidence and the head ledger remain bounded. Overflow fails without dropping supported lessons or advancing the head; review and a separately chosen new store may be necessary when history fills the budget. The legacy deterministic schema-1 catalog remains available for manually annotated principles, separately from expressive synthesis.

## Measured response evaluation

Predeclare held-out criteria for scope, depth/register, continuity, attention and permission. Use the full existing personal-agent baseline, not a weakened persona. Run actual same-route calls with and without the generated section:

```sh
python -m agent.alignment_synthesis --store REVIEW_DIR evaluate VERSION --baseline FULL_BASELINE.txt --cases HELDOUT_CASES.json > paired-receipts.json
```

Cases are `[{"name":"scenario","messages":[{"role":"user","content":"held-out request"}]}]`; direct assistant history is supported. Receipts preserve both full message sets and responses. Deterministic tests prove routing and storage contracts, not attunement. Read actual responses against the predeclared criteria. Improvements in isolated calls do not prove production/user-subjective improvement; shadow mode is not deployment. Some comparisons may be ties or regressions.

## Activate only after separate review and authorization

```sh
hermes config set alignment_synthesis.version VERSION
hermes config set alignment_synthesis.mode active
```

Default profile-scoped settings are `mode: shadow`, `version: ""`. Active injection requires an approved valid exact version; missing/invalid versions fail closed. Both catalog and expressive guidance enter new conversations after approval. Expressive guidance is pinned with an integrity digest so resumed conversations need not reread mutable artifacts or configuration. New sessions adopt changed selection; ongoing and resumed sessions retain their pinned layer. Roll back by selecting an older approved version for a new conversation.

Content addressing detects corruption, not malicious same-account writers. Generated prose is advisory, not enforcement. No live configuration, deployment, merge or scheduling is performed by this workflow.

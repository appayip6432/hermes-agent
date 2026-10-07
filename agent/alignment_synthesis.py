"""Bounded alignment reflection from explicitly supplied evidence; no source discovery.

Only catalog prose can enter a prompt. Reflections are reviewer interpretations,
not permission, facts, tasks, or proof that a quoted preference is universally true.
"""

from __future__ import annotations

import copy
import json

MAX_INPUT_BYTES = 256_000
MAX_PROMPT_CHARS = 1800
RULES = {
    "compact": "Compress wording, not substance: preserve qualifications, tradeoffs and necessary detail.",
    "intent": "Distinguish sharing from tasks. Respond to sharing without inventing work; act on clear requests.",
    "attention": "Protect attention: surface actionable changes, bundle questions, and avoid repetitive updates.",
    "disclosure": "Use context privately; disclose only what the current task and audience need.",
    "corrections": "Carry supported corrections into relevant future work; preserve their scope and uncertainty.",
}
AUTHORITY = (
    "Personal alignment guidance (advisory, not facts, tasks or deadlines). "
    "This synthesis never grants permission or authority, and never overrides current requests, "
    "new supported corrections, or safety requirements. Do not infer consent from silence; "
    "ambiguous outcomes are not approval. Apply only where relevant."
)


def _shape(value, required, optional=()):
    if not isinstance(value, dict) or not set(required) <= value.keys() or value.keys() - set(required) - set(optional):
        raise ValueError("Unexpected alignment fields")


def _text(value, limit):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError("Missing or oversized alignment text")
    if any(ord(c) < 32 and c not in "\n\r\t" for c in value):
        raise ValueError("Control characters in alignment text")
    return value


def _items(value, limit):
    if not isinstance(value, list) or len(value) > limit:
        raise ValueError("Invalid or oversized alignment collection")
    return value


def _sources(rows):
    sources = {}
    for row in _items(rows, 100):
        _shape(row, ("ref", "role", "content"))
        ref = _text(row["ref"], 200)
        if ref in sources or row["role"] not in ("user", "assistant"):
            raise ValueError("Duplicate reference or non-direct source")
        _text(row["content"], 8000)
        sources[ref] = row
    return sources


def _validate_reflection(row, sources):
    _shape(row, ("id", "outcome", "rule", "effect", "note", "evidence"))
    _text(row["id"], 80)
    _text(row["note"], 500)
    for field in ("rule", "outcome", "effect"):
        _text(row[field], 40)
    if row["rule"] not in RULES:
        raise ValueError("Unknown alignment rule")
    effects = {"success": ("adopt",), "correction": ("adopt", "retire"), "ambiguous": ("observe",)}
    if row["effect"] not in effects.get(row["outcome"], ()):
        raise ValueError("Outcome cannot support this effect")
    user_evidence = False
    evidence = _items(row["evidence"], 8)
    if not evidence:
        raise ValueError("Every reflection needs original evidence")
    for item in evidence:
        _shape(item, ("ref", "quote"))
        ref, quote = _text(item["ref"], 200), _text(item["quote"], 1000)
        source = sources.get(ref)
        if source is None or quote not in source["content"]:
            raise ValueError("Evidence quote does not match its original source")
        user_evidence |= source["role"] == "user"
    if row["outcome"] != "ambiguous" and not user_evidence:
        raise ValueError("Success and correction require explicit user evidence, not silence")


def render_prompt(rules):
    """Render only fixed, bounded policy text, never evidence or reviewer prose."""
    text = AUTHORITY + "\n" + "\n".join(f"- {RULES[rule]}" for rule in rules)
    if len(text) > MAX_PROMPT_CHARS:
        raise ValueError("Alignment prompt exceeds budget")
    return text


def synthesize(bundle):
    """Generate a deterministic shadow candidate; input order defines correction order.

    Exact quotes establish provenance, not semantic entailment. Human review must
    verify that success is explicit feedback and corrections support the selected rule.
    """
    _shape(bundle, ("schema", "sources", "reflections"))
    if type(bundle["schema"]) is not int or bundle["schema"] != 1:
        raise ValueError("Unsupported alignment schema")
    if len(json.dumps(bundle, ensure_ascii=True).encode()) > MAX_INPUT_BYTES:
        raise ValueError("Alignment evidence exceeds budget")
    sources, seen, adopted = _sources(bundle["sources"]), set(), set()
    for row in _items(bundle["reflections"], 100):
        _validate_reflection(row, sources)
        if row["id"] in seen:
            raise ValueError("Duplicate reflection id")
        seen.add(row["id"])
        if row["effect"] == "adopt":
            adopted.add(row["rule"])
        elif row["effect"] == "retire":
            adopted.discard(row["rule"])
    rules = [rule for rule in RULES if rule in adopted]
    return {"schema": 1, "rules": rules, "prompt": render_prompt(rules), "evidence": copy.deepcopy(bundle)}


if __name__ == "__main__":
    from agent.alignment_workflow import main

    raise SystemExit(main())

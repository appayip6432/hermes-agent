"""Offline, operator-driven generation and review; never searches memory or sessions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import quote

from agent.alignment_store import approve, diff_versions, load_snapshot, read_json, save_snapshot
from agent.alignment_synthesis import RULES, _items, _shape, _text, synthesize


def template():
    """Synthetic example suitable for editing, with no inferred feedback."""
    return {
        "schema": 1,
        "sources": [{"ref": "session:example/message:17", "role": "user",
                     "content": "That concise answer preserved the tradeoffs. Please keep doing that."}],
        "reflections": [{"id": "concise-feedback", "outcome": "success", "rule": "compact",
                         "effect": "adopt", "note": "Explicit feedback about wording, not removal of substance.",
                         "evidence": [{"ref": "session:example/message:17",
                                       "quote": "That concise answer preserved the tradeoffs."}]}],
    }


def prepare(export):
    """Reuse the memory checkpoint's direct-message filter on a supplied export.

    Durable row ids are required: array positions and compressed summaries are
    not original references. This adapter never opens the session database.
    """
    from agent.conversation_compression import _direct_messages_for_pre_compress_memory

    _shape(export, ("session_id", "messages"))
    session = quote(_text(export["session_id"], 100), safe="")
    rows = _direct_messages_for_pre_compress_memory(_items(export["messages"], 500))
    sources = []
    for row in rows:
        row_id = row.get("_row_id")
        if type(row_id) is not int or row_id <= 0:
            raise ValueError("Direct evidence requires an original positive message row id (_row_id)")
        sources.append({"ref": f"session:{session}/message:{row_id}",
                        "role": row["role"], "content": row.get("content")})
    bundle = {"schema": 1, "sources": sources, "reflections": []}
    synthesize(bundle)
    return bundle


def _generate(args):
    result = save_snapshot(args.store, read_json(args.input), parent=args.parent)
    return {"version": result["version"], "mode": "shadow", "rules": result["rules"],
            "next": "Review original evidence, then approve this exact version. No injection or config change occurred."}


def _review(args):
    result = load_snapshot(args.store, args.version)
    return {"snapshot": result,
            "review": "Check explicit user feedback, source authenticity, scope and minimal disclosure. Silence is not approval.",
            "diff": diff_versions(args.store, result["parent"], args.version) if result["parent"] else "Initial version"}


def _approve(args):
    if not args.confirm_reviewed:
        raise ValueError("Read review output and pass --confirm-reviewed to attest that the evidence supports each interpretation")
    approve(args.store, args.version)
    return {"approved": args.version, "injected": False,
            "next": "Opt in via alignment_synthesis.mode: active and version in config.yaml; applies only to new conversations."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", type=Path, help="Artifact directory (default: active profile's alignment directory)")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("template", help="Print a synthetic editable evidence/reflection bundle")
    sub.add_parser("catalog", help="List supported bounded principles")
    prep = sub.add_parser("prepare", help="Convert an explicitly supplied direct-message export into evidence")
    prep.add_argument("--input", type=Path, required=True)
    from agent.alignment_reflection import run_window
    nightly = sub.add_parser("nightly", help="Reflect via configured auxiliary.alignment routing on an explicit bounded export window; shadow only")
    nightly.add_argument("--input", type=Path, required=True)
    generate = sub.add_parser("generate", help="Generate a shadow snapshot; never inject")
    generate.add_argument("--input", type=Path, required=True)
    generate.add_argument("--parent", help="Extend this version without rewriting its evidence")
    for command in ("review", "validate", "approve"):
        child = sub.add_parser(command)
        child.add_argument("version")
        if command == "approve":
            child.add_argument("--confirm-reviewed", action="store_true")
    evaluate = sub.add_parser("evaluate", help="Paired real routed response receipts against an explicitly supplied full baseline")
    evaluate.add_argument("--baseline", type=Path, required=True)
    evaluate.add_argument("--cases", type=Path, required=True)
    evaluate.add_argument("version")
    diff = sub.add_parser("diff")
    diff.add_argument("old")
    diff.add_argument("new")
    args = parser.parse_args(argv)
    if args.store is None:
        from hermes_constants import get_hermes_home
        args.store = get_hermes_home() / "alignment"
    from agent.alignment_reflection import evaluate_pairs
    handlers = {
        "evaluate": lambda a: evaluate_pairs(a.baseline.read_text(encoding="utf-8-sig"), load_snapshot(a.store, a.version)["prompt"], read_json(a.cases)),
        "template": lambda _: template(), "catalog": lambda _: RULES,
        "nightly": lambda a: run_window(a.store, read_json(a.input)),
        "prepare": lambda a: prepare(read_json(a.input)), "generate": _generate,
        "review": _review, "approve": _approve,
        "validate": lambda a: {"valid": load_snapshot(a.store, a.version)["version"]},
        "diff": lambda a: diff_versions(a.store, a.old, a.new),
    }
    try:
        result = handlers[args.command](args)
    except (OSError, ValueError, TypeError) as exc:
        parser.exit(2, f"Alignment operation failed: {exc}\n")
    print(result if isinstance(result, str) else json.dumps(result, indent=2, ensure_ascii=True))
    return 0

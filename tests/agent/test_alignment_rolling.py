"""Rolling shadow history contracts; all conversation evidence is synthetic."""
import json

import pytest

from agent.alignment_reflection import run_window
from agent.alignment_store import load_snapshot, read_json


def document(name, content="Keep causal detail."):
    return {"schema": 1, "window": name, "provenance": "synthetic",
            "sources": [{"ref": name, "role": "user", "content": content}]}


def lesson(name, content="Keep causal detail.", **changes):
    return dict({"id": name, "outcome": "success", "kind": "explicit_preference",
                 "dimension": "register", "guidance": content, "scope": "explanations",
                 "evidence": [{"ref": name, "quote": content}]}, **changes)


def model(rows, revisions=None):
    return lambda _: json.dumps(dict(reflections=rows, **({"revisions": revisions} if revisions is not None else {})))


def test_worker_automatically_feeds_parent_and_retains_omitted_lessons(tmp_path):
    first = run_window(tmp_path, document("one"), model=model([lesson("one")]))
    def next_model(messages):
        prior = json.loads(messages[-1]["content"])["prior"]
        assert prior["version"] == first["version"]
        assert prior["evidence"] == first["evidence"]
        return '{"reflections": []}'
    second = run_window(tmp_path, document("two"), model=next_model)
    assert second["parent"] == first["version"]
    assert first["evidence"]["reflections"] == second["evidence"]["reflections"]
    assert read_json(tmp_path / "head.json")["version"] == second["version"]
    assert run_window(tmp_path, document("one"), model=lambda _: pytest.fail("replayed")) == first
    assert read_json(tmp_path / "head.json")["version"] == second["version"]


def test_supported_revision_records_contradiction_and_retains_original(tmp_path):
    first = run_window(tmp_path, document("one"), model=model([lesson("one")]))
    text = "For status updates, just the result."
    revision = {"target": "one", "replacement": "two", "reason": "Narrow the earlier broad register.",
                "uncertainty": "Depth still applies to causal questions."}
    second = run_window(tmp_path, document("two", text),
                        model=model([lesson("two", text, outcome="correction")], [revision]))
    assert second["parent"] == first["version"]
    assert second["evidence"]["revisions"] == [revision]
    assert "Keep causal detail." not in second["prompt"]
    assert text in second["prompt"]
    assert load_snapshot(tmp_path, first["version"]) == first


@pytest.mark.parametrize("failure", ["invalid", "unsupported", "publish", "commit"])
def test_failure_keeps_head_and_history_atomic(tmp_path, monkeypatch, failure):
    from agent import alignment_store
    first = run_window(tmp_path, document("one"), model=model([lesson("one")]))
    head = (tmp_path / "head.json").read_bytes()
    callback = lambda _: "not json"
    if failure == "unsupported":
        callback = model([lesson("two", outcome="ambiguous", kind="inference")],
                         [{"target": "one", "replacement": "two", "reason": "guess", "uncertainty": "unknown"}])
    if failure == "publish":
        callback = model([])
        original = alignment_store._publish
        def fail(path, value):
            if path.parent.name == "runs":
                raise OSError("injected disk failure")
            return original(path, value)
        monkeypatch.setattr(alignment_store, "_publish", fail)
    if failure == "commit":
        callback = model([])
        def fail_commit(*_):
            raise OSError("injected commit failure")
        monkeypatch.setattr("agent.alignment_rolling._commit_head", fail_commit)
    with pytest.raises((ValueError, OSError)):
        run_window(tmp_path, document("two"), model=callback)
    assert (tmp_path / "head.json").read_bytes() == head
    assert load_snapshot(tmp_path, first["version"]) == first
    assert len(list((tmp_path / "windows").glob("*.json"))) == 1
    assert list((tmp_path / "attempts").glob("*.json"))


def test_uncertain_offer_coexists_without_overwriting_supported_lesson(tmp_path):
    first = run_window(tmp_path, document("one"), model=model([lesson("one")]))
    export = document("two", "I could add a chart.")
    export["sources"][0]["role"] = "assistant"
    tentative = lesson("two", "I could add a chart.", outcome="ambiguous", kind="inference")
    tentative["guidance"] = "An unanswered chart offer establishes no preference."
    second = run_window(tmp_path, export, model=model([tentative]))
    assert first["evidence"]["reflections"][0] in second["evidence"]["reflections"]
    assert "Tentative inference, not established preference" in second["prompt"]
    assert "no preference" in second["prompt"]


def test_revision_rejects_reemitted_target_from_overlapping_export(tmp_path):
    first = run_window(tmp_path, document("one"), model=model([lesson("one")]))
    export = document("two", "Keep status updates short.")
    export["sources"].extend(first["evidence"]["sources"])
    revision = {"target": "one", "replacement": "two", "reason": "Status needs brevity.",
                "uncertainty": "Depth still applies to explanations."}
    head = (tmp_path / "head.json").read_bytes()
    with pytest.raises(ValueError, match="ids.*immutable"):
        run_window(tmp_path, export, model=model([
            lesson("one"), lesson("two", "Keep status updates short.", outcome="correction"),
        ], [revision]))
    assert (tmp_path / "head.json").read_bytes() == head
    assert load_snapshot(tmp_path, first["version"]) == first
    assert len(list((tmp_path / "versions").glob("*.json"))) == 1


@pytest.mark.parametrize("reuse", ["original", "changed", "replacement"])
@pytest.mark.parametrize("intervening_window", [False, True])
def test_retired_ids_cannot_be_reused_across_chain(tmp_path, reuse, intervening_window):
    first = run_window(tmp_path, document("one"), model=model([lesson("one")]))
    text = "Keep status updates short."
    revision = {"target": "one", "replacement": "two", "reason": "Status needs brevity.",
                "uncertainty": "Depth still applies to explanations."}
    second = run_window(tmp_path, document("two", text),
                        model=model([lesson("two", text, outcome="correction")], [revision]))
    if intervening_window:
        run_window(tmp_path, document("intervening"), model=model([]))
    export = document("three", "Use brief headings.")
    export["sources"].extend(first["evidence"]["sources"])
    row = lesson("one") if reuse == "original" else lesson(
        "one", "Use brief headings.", outcome="correction",
        evidence=[{"ref": "three", "quote": "Use brief headings."}])
    revisions = [dict(revision, target="two", replacement="one")] if reuse == "replacement" else None
    head = (tmp_path / "head.json").read_bytes()
    versions = set((tmp_path / "versions").glob("*.json"))
    with pytest.raises(ValueError, match="ids.*immutable"):
        run_window(tmp_path, export, model=model([row], revisions))
    assert (tmp_path / "head.json").read_bytes() == head
    assert set((tmp_path / "versions").glob("*.json")) == versions
    assert load_snapshot(tmp_path, first["version"]) == first
    assert load_snapshot(tmp_path, second["version"]) == second
    assert "one" not in {row["id"] for row in second["evidence"]["reflections"]}

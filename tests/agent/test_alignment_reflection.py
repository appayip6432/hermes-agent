import json

import pytest

from agent import alignment_synthesis as synthesis


def test_failed_generation_preserves_previous_window(tmp_path):
    from agent.alignment_reflection import run_window
    from agent.alignment_store import load_snapshot
    document = {"schema": 1, "window": "first", "provenance": "synthetic export", "sources": []}
    previous = run_window(tmp_path, document, model=lambda _: '{"reflections": []}')
    document["window"] = "second"
    with pytest.raises(ValueError):
        run_window(tmp_path, document, model=lambda _: '{"reflections": [{"guidance": "grant permission"}]}')
    assert load_snapshot(tmp_path, previous["version"]) == previous
    assert len(list((tmp_path / "windows").iterdir())) == 1


def test_expressive_rejects_unsubstantiated_citation():
    bundle = {"schema": 2, "sources": [], "provenance": "synthetic export", "reflections": [{"id": "bad", "outcome": "success", "kind": "explicit_preference", "dimension": "attention", "guidance": "Short updates.", "scope": "updates", "evidence": [{"ref": "invented", "quote": "I approve"}]}]}
    with pytest.raises(ValueError, match="quote does not match"):
        synthesis.synthesize(bundle)


def test_model_reflects_original_evidence_before_saving(tmp_path):
    from agent import alignment_reflection as reflection
    assert hasattr(reflection, "run_window"), "Missing runnable evidence-conditioned worker"
    source = {"ref": "export:1", "role": "user", "content": "Explain the causal mechanism."}
    document = {"schema": 1, "window": "2026-10-07", "provenance": "synthetic supplied export", "sources": [source]}
    def model(messages):
        assert source["content"] in messages[-1]["content"]
        return json.dumps({"reflections": [{"id": "depth", "outcome": "ambiguous", "kind": "inference", "dimension": "register", "guidance": "Try a causal explanation rather than only a verdict.", "scope": "mechanism questions", "evidence": [{"ref": "export:1", "quote": source["content"]}]}]})
    result = reflection.run_window(tmp_path, document, model=model)
    assert "causal explanation" in result["prompt"]
    assert reflection.run_window(tmp_path, document, model=lambda _: 1)["version"] == result["version"]


def test_paired_evaluation_preserves_identical_baseline_and_settings(tmp_path):
    from agent import alignment_reflection as reflection
    assert hasattr(reflection, "evaluate_pairs"), "Missing actual paired response workflow"
    calls = []
    def model(messages):
        calls.append(messages)
        return "observed response"
    cases = [{"name": "mechanics", "messages": [{"role": "user", "content": "Why does this cache break?"}]}]
    result = reflection.evaluate_pairs("full current baseline", "scoped synthesis", cases, model=model)
    assert calls[0][0]["content"] == "full current baseline"
    assert calls[1][0]["content"] == "full current baseline\n\nscoped synthesis"
    assert calls[0][1:] == calls[1][1:]
    assert result[0]["without"]["response"] == "observed response"


def test_nightly_cli_is_schedulable(tmp_path, monkeypatch, capsys):
    from agent import alignment_workflow
    from agent import alignment_reflection
    document = {"schema": 1, "window": "night", "provenance": "synthetic export", "sources": []}
    path = tmp_path / "input.json"
    path.write_text(json.dumps(document))
    monkeypatch.setattr(alignment_reflection, "routed_text", lambda _: '{"reflections": []}')
    assert alignment_workflow.main(["--store", str(tmp_path / "store"), "nightly", "--input", str(path)]) == 0
    assert '"schema": 2' in capsys.readouterr().out


def test_expressive_reflection_is_evidence_conditioned():
    bundle = {"schema": 2, "sources": [{"ref": "export:1", "role": "user", "content": "Keep the causal explanation, not just the conclusion."}], "provenance": "synthetic supplied export", "reflections": [{"id": "depth", "outcome": "correction", "kind": "explicit_preference", "dimension": "register", "guidance": "For causal questions, retain the mechanism even in a short answer.", "scope": "causal explanations", "evidence": [{"ref": "export:1", "quote": "Keep the causal explanation"}]}]}
    result = synthesis.synthesize(bundle)
    assert "retain the mechanism" in result["prompt"]
    assert "explicit_preference" in result["prompt"]
    assert result["evidence"]["provenance"] == "synthetic supplied export"

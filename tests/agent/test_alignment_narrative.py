import pytest

from agent.alignment_synthesis import synthesize


def bundle():
    text = 'The user relies on follow-through, but what care means outside technical work is uncertain.'
    return {'schema': 2, 'provenance': 'test original export', 'sources': [{'ref': 'u1', 'role': 'user', 'content': 'Please finish it and verify.'}], 'reflections': [], 'narrative': {'text': text, 'claims': [{'span': text, 'status': 'tentative', 'evidence': [{'ref': 'u1', 'quote': 'Please finish it and verify.'}]}]}}


def test_narrative_is_integrated_prose_with_separate_audit():
    data = bundle()
    result = synthesize(data)
    assert result['prompt'].endswith(data['narrative']['text'])
    assert 'tentative' not in result['prompt']
    assert result['evidence']['narrative']['claims'] == data['narrative']['claims']


def test_worker_publishes_model_narrative(tmp_path):
    import json
    from agent.alignment_reflection import run_window
    data = bundle()
    document = {'schema': 1, 'window': 'one', 'provenance': data['provenance'], 'sources': data['sources']}
    response = {'reflections': [], 'narrative': data['narrative']}
    result = run_window(tmp_path, document, model=lambda _: json.dumps(response))
    assert result['prompt'].endswith(data['narrative']['text'])


def test_long_narrative_frame_survives_resume():
    from agent.alignment_prompt import _expressive_frame, _restore
    from agent.alignment_synthesis import AUTHORITY
    prompt = AUTHORITY + '\n\n' + 'Grounded provisional understanding. ' * 100
    frame = _expressive_frame('a' * 64, prompt)
    assert _restore(frame) == frame


def test_paired_evaluation_accepts_narrative_depth():
    from agent.alignment_reflection import evaluate_pairs
    result = evaluate_pairs('baseline', 'provisional understanding ' * 100,
                            [{'name': 'heldout', 'messages': [{'role': 'user', 'content': 'Help.'}]}],
                            model=lambda _: 'response')
    assert result[0]['with']['response'] == 'response'


def test_rolling_narrative_can_ground_retained_understanding(tmp_path):
    import json
    from agent.alignment_reflection import run_window
    data = bundle()
    first = {'schema': 1, 'window': 'one', 'provenance': data['provenance'], 'sources': data['sources']}
    response = {'reflections': [], 'narrative': data['narrative']}
    previous = run_window(tmp_path, first, model=lambda _: json.dumps(response))
    second = dict(first, window='two', sources=[{'ref': 'u2', 'role': 'user', 'content': 'Thanks.'}])
    result = run_window(tmp_path, second, model=lambda _: json.dumps(response))
    assert result['parent'] == previous['version']
    assert len(result['evidence']['sources']) == 2


def test_narrative_rejects_unmapped_prose():
    data = bundle()
    data['narrative']['text'] += ' Unmapped assertion.'
    with pytest.raises(ValueError, match='coverage'):
        synthesize(data)

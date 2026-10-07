"""Integrated prose with separately retained, exact-source claim mappings."""
from agent.alignment_synthesis import _items, _shape, _text

MAX_NARRATIVE_CHARS = 6000


def validate_narrative(value, sources):
    _shape(value, ('text', 'claims'))
    text = _text(value['text'], MAX_NARRATIVE_CHARS)
    covered = [False] * len(text)
    for claim in _items(value['claims'], 32):
        _shape(claim, ('span', 'status', 'evidence'))
        span = _text(claim['span'], MAX_NARRATIVE_CHARS)
        if claim['status'] not in ('supported', 'tentative') or span not in text:
            raise ValueError('Invalid narrative claim mapping')
        evidence = _items(claim['evidence'], 8)
        if not evidence:
            raise ValueError('Narrative claim needs evidence')
        human = False
        for item in evidence:
            _shape(item, ('ref', 'quote'))
            ref, quote = _text(item['ref'], 200), _text(item['quote'], 1000)
            if ref not in sources or quote not in sources[ref]['content']:
                raise ValueError('Narrative quote does not match original source')
            human |= sources[ref]['role'] == 'user'
        if claim['status'] == 'supported' and not human:
            raise ValueError('Supported narrative claim requires human evidence')
        start = text.index(span)
        covered[start:start + len(span)] = [True] * len(span)
    if any(not marked and not char.isspace() for char, marked in zip(text, covered)):
        raise ValueError('Narrative claim coverage is incomplete')
    return text


NARRATIVE_PROMPT = """
Also return narrative: {text, claims: [{span, status, evidence: [{ref, quote}]}]}.
Text is an integrated short behavioral portrait, normally 300-700 words, at most 6000
characters, NOT a checklist, category bullets, concatenated lessons or five schema headings.
Weave together: what the user relies on the agent for; tensions the agent should understand;
what care looks like in practice; how recent interactions change the prior understanding;
and where the interpretation is uncertain. Connect motives, tensions and concrete behavior
without inventing biography or psychological diagnosis. Qualify tentative interpretations in
natural prose. Absence of evidence is a limitation, not evidence of a trait. Every non-whitespace
character must be covered by an exact span in claims (paragraph spans are acceptable).
Claims are structured provenance separately from prose, with supported/tentative status and
exact original quotes. Citations establish provenance, not entailment; human review remains
required. Use prior narrative as a provisional understanding to meaningfully revise or reaffirm
in light of the new window, never as fresh human evidence. Historical permissions are not
current authorization. Reflections underneath are an audit ledger, not the narrative itself.
"""

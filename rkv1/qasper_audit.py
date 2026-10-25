"""Offline retrieval and context coverage diagnostics, never answer grading.

Annotations are kept separate from indexed paper projections. No model service
or credentials are read. These metrics are not official QASPER Answer/Evidence F1.
"""
import json

from .core import digest
from .memory import _json
from .memory_model import exposed_hits
from .memory_qasper import records, unique

BUDGETS = (8000, 24000, 48000)


def cases(raw):
    """Read human question/evidence labels only for a separate offline scorer."""
    docs = json.loads(raw, object_pairs_hook=unique)
    if not isinstance(docs, dict): raise ValueError('QASPER audit requires a paper object')
    paper_text = {r[0]: [s.strip() for s in r[2]] for r in records(raw, 1 << 20)}
    result = []; seen = set()
    for paper_id, paper in sorted(docs.items()):
        if not isinstance(paper.get('qas'), list): raise ValueError('QASPER audit requires qas labels')
        for qa in paper['qas']:
            if not isinstance(qa, dict): raise ValueError('Invalid QASPER question object')
            qid = qa.get('question_id'); question = qa.get('question'); answers = qa.get('answers')
            if (not isinstance(qid, str) or not qid or qid in seen or not isinstance(question, str)
                    or not question.strip() or not isinstance(answers, list) or not answers):
                raise ValueError('Invalid or duplicate QASPER audit question')
            seen.add(qid); refs = []; flags = []
            for info in answers:
                if not isinstance(info, dict): raise ValueError('Invalid QASPER annotation object')
                answer = info.get('answer', {})
                if not isinstance(answer, dict) or type(answer.get('unanswerable')) is not bool or not isinstance(answer.get('evidence'), list) or not all(isinstance(s,str) for s in answer['evidence']):
                    raise ValueError('Invalid QASPER answerability/evidence annotation')
                flags.append(answer['unanswerable'])
                if not answer['unanswerable']:
                    evidence = sorted({s.strip() for s in answer['evidence'] if s.strip()})
                    if evidence: refs.append(evidence)
            key = 'qasper:' + paper_id; available = set(paper_text[key])
            result.append({'question_id_sha256': digest(qid.encode()), 'question_sha256': digest(question.encode()),
                'question': question, 'paper_key': key, 'gold_sets': refs,
                'answerability': 'all-unanswerable' if all(flags) else 'mixed' if any(flags) else 'all-answerable',
                'annotation_count': len(answers), 'fully_text_mapped_reference': any(set(ref) <= available for ref in refs),
                'gold_evidence_strings': sum(len(ref) for ref in refs),
                'unmapped_evidence_strings': sum(s not in available for ref in refs for s in ref)})
    return result


def score(case, hits, *, budget=24000, top_k=5):
    """Exact paragraph-string coverage of any nonempty answerable reference.

Only outer whitespace is normalized. Unmapped evidence (including tables) stays
in the denominator. A retrieved wrong paper cannot earn gold coverage.
"""
    if type(budget) is not int or budget < 0 or type(top_k) is not int or top_k < 1:
        raise ValueError('Invalid context audit budget/top_k')
    if any(not h.get('source_bytes_verified') for h in hits):
        raise ValueError('Context audit requires verified source hits')
    visible = exposed_hits(hits[:top_k], budget=budget)
    selected = {s.strip() for h in visible if h['key'] == case['paper_key'] for i in h['visible_sentence_ids'] for s in [h['sentences'][i]]}
    refs = [set(ref) for ref in case['gold_sets']]
    complete = any(ref <= selected for ref in refs) if refs else None
    recall = max(len(ref & selected)/len(ref) for ref in refs) if refs else None
    rank = next((i+1 for i,h in enumerate(hits) if h['key'] == case['paper_key']), None)
    if not refs: reason = 'no-nonempty-answerable-reference'
    elif rank is None or rank > top_k: reason = 'parent-not-top-k'
    elif complete: reason = 'complete-reference-exposed'
    elif not case['fully_text_mapped_reference']: reason = 'no-fully-text-mapped-reference'
    else: reason = 'budget-omitted-reference'
    body_bytes = sum(len(h['sentences'][i].encode()) for h in visible for i in h['visible_sentence_ids'])
    assert body_bytes <= budget
    # This accounts for the context object including titles/IDs/JSON overhead,
    # but excludes the question/system prompt/API envelopes and tokenization.
    context = [{'citation_id': h['citation_id'], 'title': h['title'],
                'sentences': [{'sentence': i, 'text': h['sentences'][i]} for i in h['visible_sentence_ids']]} for h in visible]
    return {'budget_body_utf8_bytes': budget, 'top_k': top_k, 'parent_rank_in_retrieved': rank,
            'complete_reference_exposed': complete, 'best_reference_paragraph_recall': recall,
            'failure_or_success_reason': reason, 'visible_body_utf8_bytes': body_bytes,
            'serialized_context_json_bytes': len(_json(context)),
            'visible_papers': len(visible), 'visible_paragraphs': sum(len(h['visible_sentence_ids']) for h in visible)}

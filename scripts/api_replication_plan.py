"""Fixed second-cohort API replication selection; no retrieval or transport."""
from scripts.api_intervention import sha, gold_label, CONDITIONS
from scripts.evidence_retrieval import question_identity

def select_replication(claims, excluded_ids=(), excluded_questions=()):
    if len({str(c['id']) for c in claims}) != len(claims):
        raise ValueError('Duplicate claim ID')
    banned_ids = set(map(str, excluded_ids))
    banned_questions = {question_identity(q) for q in excluded_questions}
    selected, seen = [], set()
    for label, count in (('SUPPORT', 6), ('CONTRADICT', 6), ('INSUFFICIENT', 4)):
        eligible = [c for c in claims if str(c['id']) not in banned_ids
                    and question_identity(c['claim']) not in banned_questions
                    and gold_label(c) == label]
        eligible.sort(key=lambda c: (sha(('rkv087-claim:' + str(c['id'])).encode()), str(c['id'])))
        chosen = []
        for c in eligible:
            q = question_identity(c['claim'])
            if q in seen:
                continue
            chosen.append(c)
            seen.add(q)
            if len(chosen) == count:
                break
        if len(chosen) != count:
            raise ValueError('Insufficient disjoint stratum')
        selected.extend(chosen)
    selected.sort(key=lambda c: (sha(('rkv087-donor:' + str(c['id'])).encode()), str(c['id'])))
    ids = [str(c['id']) for c in selected]
    donors = {i: ids[(j + 1) % len(ids)] for j, i in enumerate(ids)}
    jobs = [{'claim_id': i, 'condition': c, 'donor_claim_id': donors[i] if c == 'rotated' else i}
            for i in ids for c in CONDITIONS]
    jobs.sort(key=lambda j: sha(('rkv087-order:' + j['claim_id'] + ':' + j['condition']).encode()))
    return {'selected_claim_ids': ids, 'jobs': jobs,
            'class_counts': {'SUPPORT': 6, 'CONTRADICT': 6, 'INSUFFICIENT': 4},
            'no_unseen_data_claim': True}

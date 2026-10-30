"""Postprediction annotation-availability metrics; not model answer scores."""


def score(available, evidence):
    if type(available) is not dict or type(evidence) is not dict:
        raise ValueError('Original source selection and annotation maps required')
    selected={}
    for key, indices in available.items():
        if type(key) is not str or not key.startswith('doc:') or type(indices) is not list or any(type(i) is not int or i<0 for i in indices) or len(indices)!=len(set(indices)):
            raise ValueError('Explicit original source indices required')
        selected[key[4:]]=set(indices)
    if not evidence:
        return {'annotated':False,'paper_recall':None,'complete_rationale_available':None,'not_evidence_of_no_support':True}
    matched=0;complete=False
    for paper, alternatives in evidence.items():
        if type(paper) is not str or type(alternatives) is not list or not alternatives:
            raise ValueError('Original paper and rationale alternatives required')
        if paper in selected:matched+=1
        for row in alternatives:
            indices=row.get('sentences') if type(row) is dict else None
            if type(indices) is not list or not indices or any(type(i) is not int or i<0 for i in indices) or len(set(indices))!=len(indices):
                raise ValueError('Nonempty original rationale indices required')
            if set(indices)<=selected.get(paper,set()):complete=True
    return {'annotated':True,'paper_recall':matched/len(evidence),'complete_rationale_available':complete,
            'any_complete_alternative_not_all_groups_conjunction':True,'scientific_entailment_or_answer_correctness_measured':False}

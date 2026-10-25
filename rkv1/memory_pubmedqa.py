"""Exact PubMedQA members; only original CONTEXTS are evidence text.

The explicit .pubmedqa.json suffix prevents confusing this schema with QASPER.
Question, long answer, decisions, predictions and section metadata are retained
in the original byte record but never projected into retrieval or model context.
"""
from .memory_qasper import members

KIND='pubmedqa-json-member-v1'


def records(raw,limit):
    for pmid,obj,offset,original in members(raw):
        if (not pmid.isascii() or not pmid.isdigit() or not 1<=len(pmid)<=16 or pmid[0]=='0'):
            raise ValueError('Invalid PubMedQA positive ASCII PMID')
        if len(original)>limit:raise ValueError('Evidence record exceeds 1 MiB')
        if (not isinstance(obj,dict) or not isinstance(obj.get('CONTEXTS'),list)
                or not all(isinstance(s,str) for s in obj['CONTEXTS'])):
            raise ValueError('PubMedQA evidence requires CONTEXTS strings')
        # The source has no separate article title. The question must not be
        # substituted for it, since that would leak the retrieval query.
        yield 'pubmedqa:'+pmid,'PMID '+pmid,list(obj['CONTEXTS']),offset,original,KIND

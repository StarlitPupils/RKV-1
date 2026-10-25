"""Explicit lexical paragraph selection over already verified retrieved papers.

No annotations, model, embeddings or persistent index. Returned sentence IDs
still address the original source hits. Source-order remains the model default.
"""
import re
import sqlite3

from .memory import STOP


def lexical_order(question, hits):
    """Rank paragraph bodies with query-local FTS5; unmatched rows follow source order."""
    if not isinstance(question,str) or not 1<=len(question)<=4096:
        raise ValueError('Invalid paragraph-selection question')
    if any(h.get('source_bytes_verified') is not True for h in hits):
        raise ValueError('Paragraph selection requires verified source hits')
    positions=[(d,i) for d,h in enumerate(hits) for i in range(len(h['sentences']))]
    tokens=list(dict.fromkeys(t.lower() for t in re.findall(r'[\w]+',question,re.UNICODE) if t.lower() not in STOP and len(t)>1))[:64]
    if not tokens or not positions:return positions
    db=sqlite3.connect(':memory:')
    try:
        db.execute("CREATE VIRTUAL TABLE paragraphs USING fts5(body,content='',tokenize='porter unicode61')")
        db.executemany('INSERT INTO paragraphs(rowid,body) VALUES(?,?)',[(row+1,hits[d]['sentences'][i]) for row,(d,i) in enumerate(positions)])
        match=' OR '.join('"'+t+'"' for t in tokens)
        rows=[r[0]-1 for r in db.execute('SELECT rowid FROM paragraphs WHERE paragraphs MATCH ? ORDER BY bm25(paragraphs),rowid',(match,))]
        selected=set(rows)
        return [positions[i] for i in rows]+[p for i,p in enumerate(positions) if i not in selected]
    finally:db.close()


def choose(hits, order, *, budget=24000):
    """Consume the same body UTF-8 budget as exposed_hits, preserving original IDs."""
    if type(budget) is not int or budget<0:raise ValueError('Invalid paragraph-selection budget')
    expected={(d,i) for d,h in enumerate(hits) for i in range(len(h['sentences']))}
    if (not isinstance(order,list) or any(not isinstance(p,tuple) or len(p)!=2 or any(type(i) is not int for i in p) for p in order)
            or len(order)!=len(expected) or set(order)!=expected):
        raise ValueError('Paragraph order must contain every source position exactly once')
    if any(h.get('source_bytes_verified') is not True for h in hits):raise ValueError('Paragraph selection requires verified source hits')
    chosen={};remaining=budget
    for d,i in order:
        n=len(hits[d]['sentences'][i].encode('utf-8'))
        if n<=remaining:chosen.setdefault(d,[]).append(i);remaining-=n
    return [{**h,'visible_sentence_ids':sorted(chosen[d])} for d,h in enumerate(hits) if d in chosen]

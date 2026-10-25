"""Exact original eLife JATS articles with a bounded lexical text projection.

The record is the whole XML file: no rewritten JSON or reconstructed XML is
presented as original evidence. Inline markup is text-projected only for FTS.
"""
import re
import xml.etree.ElementTree as ET
from xml.parsers import expat

KIND='elife-jats-article-v1'
EXCLUDE={'fig','table-wrap','supplementary-material','boxed-text','ref-list','fn-group','sub-article','response'}


def reject(*args):raise ValueError('JATS entity declarations and external entities are unsupported')


def parse(raw):
    builder=ET.TreeBuilder();parser=expat.ParserCreate()
    parser.StartElementHandler=builder.start;parser.EndElementHandler=builder.end;parser.CharacterDataHandler=builder.data
    parser.EntityDeclHandler=reject;parser.ExternalEntityRefHandler=reject
    parser.SetParamEntityParsing(expat.XML_PARAM_ENTITY_PARSING_NEVER)
    try:parser.Parse(raw,True);root=builder.close()
    except (expat.ExpatError,ET.ParseError) as exc:raise ValueError('Invalid JATS XML') from exc
    if root.tag!='article' or root.get('article-type')!='research-article':raise ValueError('JATS requires an unnamespaced research article')
    meta=root.find('front/article-meta')
    if meta is None:raise ValueError('JATS article metadata missing')
    ids=[(e.text or '').strip() for e in meta.findall('article-id') if e.get('pub-id-type')=='publisher-id']
    dois=[(e.text or '').strip() for e in meta.findall('article-id') if e.get('pub-id-type')=='doi' and not e.get('specific-use')]
    if len(ids)!=1 or not re.fullmatch(r'[0-9]{1,12}',ids[0]) or dois!=['10.7554/eLife.'+ids[0]]:
        raise ValueError('JATS requires a unique matching eLife publisher ID and base DOI')
    titles=meta.findall('title-group/article-title');body=root.findall('body')
    if len(titles)!=1 or len(body)!=1:raise ValueError('JATS requires one title and body')
    text=lambda el:''.join(el.itertext()).strip()
    title=text(titles[0]);paragraphs=[]
    def visit(el):
        if el.tag in EXCLUDE:return
        if el.tag=='p':
            # A paragraph is one projected unit; do not duplicate nested p text.
            paragraphs.append(text(el));return
        for child in el:visit(child)
    for abstract in meta.findall('abstract'):
        if not abstract.get('abstract-type'):visit(abstract)
    visit(body[0])
    if not title or not paragraphs or not any(paragraphs):raise ValueError('JATS title/body projection is empty')
    return 'elife:'+ids[0],title,paragraphs


def records(raw,limit):
    if len(raw)>limit:raise ValueError('Evidence record exceeds 1 MiB')
    key,title,paragraphs=parse(raw)
    yield key,title,paragraphs,0,raw,KIND

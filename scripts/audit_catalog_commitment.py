"""Experimental standalone verifier, separate iterative root reconstruction; no Store/builder imports."""
import hashlib,re
from scripts.postings_transform import canonical
HEX=re.compile('[0-9a-f]{64}\\Z');PATH=re.compile(r'[a-z][a-z0-9_-]*(?:/[a-z][a-z0-9_-]*)*\.logic\.jsonl\Z')
def ishash(x):return type(x) is str and HEX.fullmatch(x) is not None
def verify(anchor,proof,raw,*,expected_anchor_sha256,expected_snapshot_id,expected_path,source_byte_budget=1<<20):
 if not ishash(expected_anchor_sha256) or not ishash(expected_snapshot_id) or type(expected_path) is not str or not PATH.fullmatch(expected_path) or type(source_byte_budget) is not int or not 0<=source_byte_budget<=1<<20:raise ValueError('External trusted anchor/SID/path and bounded payload required')
 if type(anchor) is not dict or set(anchor)!={'format','snapshot_id','eligible_count','eligible_payload_B','root_sha256'} or anchor['format']!='RKVCATALOGANCHOR1' or anchor['snapshot_id']!=expected_snapshot_id or type(anchor['eligible_count']) is not int or not 1<=anchor['eligible_count']<=4096 or type(anchor['eligible_payload_B']) is not int or not 0<=anchor['eligible_payload_B']<4096*(1<<63) or not ishash(anchor['root_sha256']):raise ValueError('Strict trusted anchor schema required')
 if hashlib.sha256(canonical(anchor)).hexdigest()!=expected_anchor_sha256:raise ValueError('Externally supplied anchor identity differs')
 if type(proof) is not dict or set(proof)!={'format','snapshot_id','anchor_sha256','leaf_index','entry','siblings'} or proof['format']!='RKVCATALOGMEMBER1' or proof['snapshot_id']!=expected_snapshot_id or proof['anchor_sha256']!=expected_anchor_sha256:raise ValueError('Membership proof anchor or schema differs')
 n=anchor['eligible_count'];index=proof['leaf_index'];e=proof['entry'];siblings=proof['siblings']
 if type(index) is not int or not 0<=index<n or type(siblings) is not list or len(siblings)>12 or any(not ishash(x) for x in siblings):raise ValueError('Bounded leaf index and path required')
 if type(e) is not dict or set(e)!={'path','bytes','sha256'} or e['path']!=expected_path or len(expected_path)>240 or type(e['bytes']) is not int or not 0<=e['bytes']<1<<63 or e['bytes']>anchor['eligible_payload_B'] or e['bytes']>source_byte_budget or not ishash(e['sha256']):raise ValueError('Original path/size/hash entry differs')
 if type(raw) is not bytes or len(raw)!=e['bytes'] or hashlib.sha256(raw).hexdigest()!=e['sha256']:raise ValueError('Exact original payload required')
 # Work out the unique unbalanced tree route independently of proof generation.
 route=[]
 while n>1:
  cut=2**((n-1).bit_length()-1)
  if index<cut:route.append('right');n=cut
  else:route.append('left');index-=cut;n-=cut
 if len(siblings)!=len(route):raise ValueError('Missing or trailing sibling')
 value=hashlib.sha256(bytes([0])+canonical(e)).digest()
 for direction,sibling in zip(reversed(route),siblings):
  other=bytes.fromhex(sibling);value=hashlib.sha256(bytes([1])+(value+other if direction=='right' else other+value)).digest()
 if value.hex()!=anchor['root_sha256']:raise ValueError('Membership root differs')
 return {'original_selected_bytes_membership_verified':True,'snapshot_id':expected_snapshot_id,'path':expected_path,'application_payload_B':len(raw),'full_eligible_coverage_verified':False,'logic_verified':False,'scientific_entailment_verified':False,'anchor_requires_prior_trusted_full_manifest_validation':True}

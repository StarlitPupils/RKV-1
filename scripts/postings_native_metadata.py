"""Create explicit build provenance for experimental postings batch ABI."""
import argparse,hashlib,json,os,platform,subprocess
from pathlib import Path

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('library');p.add_argument('--output',required=True);args=p.parse_args();library=Path(args.library)
    from scripts.native_postings import PairReader
    sha=hashlib.sha256(library.read_bytes()).hexdigest();reader=PairReader(b'\x01\x02',library,sha);values,used=reader.pairs(0,1);assert list(values)[:2]==[1,2] and used==2
    meta={'abi':1,'library':library.name,'sha256':sha,'bytes':library.stat().st_size,'source_commit':os.environ.get('GITHUB_SHA') or subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'rustc':subprocess.check_output(['rustc','--version'],text=True).strip(),'platform':platform.platform(),'features':['canonical-u64-batch-v1'],'compile_options':{'opt-level':3,'lto':True,'codegen-units':1,'panic':'abort','strip':True,'third_party_crate_dependencies':0},'scope':'Allocation-free canonical u64 reader only. Caller buffers and Python/frame validation still required. Performance applies only to the explicitly measured binary.'}
    with Path(args.output).open('x',encoding='utf-8') as stream:json.dump(meta,stream,indent=2);stream.write('\n')
    print(json.dumps(meta))

if __name__=='__main__':main()

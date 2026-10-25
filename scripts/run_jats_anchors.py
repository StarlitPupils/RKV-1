"""Frozen content-anchor versus positional/whole adjacent-budget experiment."""
import argparse
from pathlib import Path
from scripts.run_jats_fragments import main, worker, units

MODES=('whole','position','content')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path);p.add_argument('--work',type=Path);p.add_argument('--native-library',type=Path)
    p.add_argument('--worker',action='store_true');p.add_argument('--mode',choices=MODES);p.add_argument('--round',type=int);p.add_argument('--result',type=Path)
    a=p.parse_args()
    if a.worker:worker(a)
    else:main(a,modes=MODES,fragment_modes=('position','content'),worker_module='scripts.run_jats_anchors',label_prefix='v025-anchors')

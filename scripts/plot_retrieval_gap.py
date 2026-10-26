"""Plot-only explicit stacked-axis headroom; never rerun diagnostic/score logic."""
import argparse
import json
import os
from pathlib import Path
import time
from rkv1.core import digest
from scripts.run_memory_concurrency import save


def main():
    begin=time.perf_counter();cpu=time.process_time();p=argparse.ArgumentParser()
    p.add_argument('--metrics',required=True);p.add_argument('--out',required=True);p.add_argument('--timing',required=True);args=p.parse_args()
    raw=Path(args.metrics).read_bytes();data=json.loads(raw)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    categories=('recovered','unresolved_source','no_candidate','below_count_prefix','byte_budget_excluded')
    colors=('#10b981','#dc2626','#f59e0b','#2563eb','#9333ea')
    fig,axes=plt.subplots(1,2,figsize=(14,5.5),layout='constrained')
    for ax,split in zip(axes,('dev','test')):
        rr=[r for r in data['rows'] if r['split']==split];bottom=[0]*3
        for category,color in zip(categories,colors):
            values=[r['counts'][category] for r in rr]
            ax.bar(range(3),values,bottom=bottom,label=category,color=color)
            bottom=[a+b for a,b in zip(bottom,values)]
        top=max(bottom);ax.set_ylim(0,top*1.12)
        for x,total in enumerate(bottom):ax.text(x,total+top*.02,str(total),ha='center',va='bottom',fontsize=9)
        ax.set_xticks(range(3),[r['method'] for r in rr]);ax.set_title(split+': fixed source-ID group positions')
        ax.set_ylabel('Gold groups, archived split');ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
    handles,labels=axes[0].get_legend_handles_labels();fig.legend(handles,labels,loc='outside lower center',ncol=3,frameon=False,fontsize=9)
    fig.suptitle('RKV-1 v0.52: known-report failure ledger; no new retrieval trial, gold-aware bounds diagnostic only')
    with Path(args.out).open('xb') as stream:fig.savefig(stream,format='png',dpi=160);stream.flush();os.fsync(stream.fileno())
    plt.close(fig)
    save(args.timing,{'metrics_sha256':digest(raw),'figure_sha256':digest(Path(args.out).read_bytes()),'plot_only_wall_s':time.perf_counter()-begin,
        'plot_only_cpu_s':time.process_time()-cpu,'scope':'Plot only explicit axis bounds and totals; no classification, model, score or oracle recomputation'})


if __name__=='__main__':main()

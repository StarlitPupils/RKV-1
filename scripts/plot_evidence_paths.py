"""Render aggregate-only report figure with legends outside data panels."""
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--metrics',required=True);p.add_argument('--output',required=True)
    args=p.parse_args();rows=json.loads(Path(args.metrics).read_text('utf-8'))['rounds'];x=[r['round'] for r in rows]
    fig,axes=plt.subplots(1,3,figsize=(14,5.7),layout='constrained')
    axes[0].bar(x,[r['complete'] for r in rows],label='Complete (93 expected)',color='#2563eb')
    axes[0].bar(x,[r['expected_missing_or_cycle'] for r in rows],bottom=[r['complete'] for r in rows],label='Missing/cycle (3 expected)',color='#d97706')
    axes[0].set_ylabel('Main queries (96 per round)');axes[0].set_title('Correct statuses, not model answers')
    axes[1].bar(x,[r['before_query_bytes']/1024 for r in rows],label='Stored sources/index/history',color='#64748b')
    axes[1].bar(x,[r['derived_added_bytes']/1024 for r in rows],bottom=[r['before_query_bytes']/1024 for r in rows],label='Derived path records',color='#16a34a')
    axes[1].set_ylabel('KiB, full memory file tree');axes[1].set_title('All persistent memory files charged')
    for index,(field,label,color) in enumerate((('ingest_wall_s','13 ingests','#64748b'),('trace_wall_s','100 traces','#2563eb'),
               ('independent_audit_wall_s','100 original-record audits','#d97706'),('derived_write_wall_s','100 derived writes','#16a34a'))):
        axes[2].bar([n+(index-1.5)*.18 for n in x],[r[field] for r in rows],.17,label=label,color=color)
    axes[2].set_ylabel('Seconds (log)');axes[2].set_yscale('log');axes[2].set_title('Wall time by separately charged stage')
    for ax in axes:
        ax.set_xticks(x,[f'Round {n}' for n in x]);ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
        ax.legend(loc='upper center',bbox_to_anchor=(.5,-.12),fontsize=8,frameon=False)
    axes[0].set_ylim(0,110)
    axes[1].set_ylim(0,max(r['final_memory_bytes']/1024 for r in rows)*1.08)
    fig.suptitle('RKV-1 v0.40: synthetic known-root / specified-SID explicit evidence paths')
    fig.savefig(args.output,dpi=160);plt.close(fig)


if __name__=='__main__':main()

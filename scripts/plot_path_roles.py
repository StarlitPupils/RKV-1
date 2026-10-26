"""Plot-only headroom correction from frozen aggregate; never recompute scores."""
import argparse
import json
from pathlib import Path
import time
from rkv1.benchmark import peak_rss
from scripts.run_memory_concurrency import save


def main():
    began=time.perf_counter();cpu=time.process_time()
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',required=True);p.add_argument('--out',required=True);p.add_argument('--stats',required=True)
    args=p.parse_args();data=json.loads(Path(args.input).read_text('utf-8'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    names=('clustered','separated');roles=('manifest_validation','index_view','source_hit','other_trace')
    colors=('#f59e0b','#8b5cf6','#2563eb','#94a3b8')
    chosen=[next(r for r in data['rows'] if r['round']==1 and r['layout']==layout) for layout in names]
    for layout in names:
        same=[r for r in data['rows'] if r['layout']==layout]
        assert len(same)==3 and all(r['roles']==same[0]['roles'] for r in same)
    fig,axes=plt.subplots(1,2,figsize=(12,6),layout='constrained')
    for ax,key in zip(axes,('CAS_decoded_output_bytes','application_CAS_file_bytes')):
        bottoms=[0.,0.]
        for role,color in zip(roles,colors):
            values=[r['roles'][role]['traffic'][key]/(1<<20) for r in chosen]
            ax.bar(names,values,bottom=bottoms,label=role,color=color)
            bottoms=[a+b for a,b in zip(bottoms,values)]
        ax.set_ylim(0,max(bottoms)*1.12)
        for i,total in enumerate(bottoms):ax.text(i,total+max(bottoms)*.018,f'{total:.2f}',ha='center',fontsize=9)
        ax.set_ylabel('MiB / 100 traces');ax.set_title('CAS decoded output' if key.startswith('CAS_') else 'Application CAS read returns')
        ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
    fig.legend(*axes[0].get_legend_handles_labels(),loc='outside lower center',ncol=2,frameon=False)
    fig.suptitle('RKV-1 v0.44: original CAS work by exclusive call-entry role, cache OFF\nRound 1 shown; all three paired rounds retained; no timing-benefit claim')
    fig.savefig(args.out,dpi=160);plt.close(fig)
    save(args.stats,{'wall_s':time.perf_counter()-began,'cpu_s':time.process_time()-cpu,'observed_peak_rss_bytes':peak_rss(),
        'scope':'Plot-only postmeasurement, includes matplotlib import; excludes interpreter startup and this stats write; frozen raw scores/initial figure unchanged'})


if __name__=='__main__':main()

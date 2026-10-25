"""Audit original PubMedQA projection and paired source-ID retrieval transfer."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import subprocess

from rkv1.controlled import implementation_checksums
from rkv1.core import digest
from rkv1.memory_pubmedqa import records
from scripts.analyze_known_source import dist, mean
from scripts.analyze_paragraph_retrieval import paired
from scripts.run_paragraph_retrieval import RETRIEVERS, KS, parent_metrics
from scripts.run_pubmedqa_transfer import load, SHA, OLD_WHEEL_SHA, URL, COMMIT
from scripts.run_units import save
from scripts.summarize_units import table


def analyze(root,input_path,log,frozen):
    read=lambda n:json.loads((root/n).read_text('utf-8'))
    checks=read('source-checksums.json');assert len(checks)==55 and checks==implementation_checksums()
    for name,sha in checks.items():assert digest(subprocess.check_output(['git','show',frozen+':rkv1/'+name]))==sha
    for rel in ('docs/PUBMEDQA-TRANSFER.md','scripts/run_pubmedqa_transfer.py'):
        assert Path(rel).read_bytes()==subprocess.check_output(['git','show',frozen+':'+rel])
    resources=read('source-resource.json');assert resources['total_bytes']==sum(v['bytes'] for v in resources['files'].values())
    assert set(resources['files'])=={'rkv1/'+n for n in checks}|{'rkv1/memory_demo.html'}
    for name,v in resources['files'].items():assert digest(Path(name).read_bytes())==v['sha256'] and Path(name).stat().st_size==v['bytes']
    post=read('postconditions.json');assert all(post[k] for k in ('all_original_bytes_restored','Memory_and_auxiliary_trees_unchanged','checksums_unchanged')) and post['remote_model_calls']==0
    compatibility=read('algorithm-compatibility.json');assert all(compatibility[k] for k in ('best_unit_module_byte_identical','whole_paper_search_verified_hits_and_lookup_AST_identical','STOP_definition_AST_identical','no_ranking_parameter_change'))
    assert compatibility['best_unit_module_sha256']==digest(Path('rkv1/memory_paragraph.py').read_bytes())
    legacy=read('legacy-reader-probe.json');assert legacy['actual_v030_wheel_sha256']==OLD_WHEEL_SHA and all(v is True for k,v in legacy.items() if k!='actual_v030_wheel_sha256')
    raw,jobs=load(input_path);docs=json.loads(raw);labels={c['question_id_sha256']:c for c in jobs};projected=list(records(raw,1<<20))
    assert digest(raw)==SHA and len(projected)==1000
    for key,title,body,off,original,kind in projected:
        pmid=key.removeprefix('pubmedqa:');assert title=='PMID '+pmid and body==docs[pmid]['CONTEXTS']
        assert raw[off:off+len(original)]==original and kind=='pubmedqa-json-member-v1'
    normalized=lambda ss:digest(' '.join(' '.join(s.split()) for s in ss).encode())
    duplicates=Counter(normalized(r[2]) for r in projected)
    trials=[read(f'round{r}.json') for r in range(3)];first=trials[0]['queries'];idx={r['question_id_sha256']:r for r in first}
    assert len(first)==len(idx)==1000 and set(idx)==set(labels);formal=0
    for rr,t in enumerate(trials):
        assert t['round']==rr and t['warmup_read_operations']==2 and t['Memory_and_auxiliary_trees_unchanged'] and t['generation_calls']==0
        assert len(t['queries'])==1000 and {r['question_id_sha256'] for r in t['queries']}==set(labels)
        for r in t['queries']:
            c=labels[r['question_id_sha256']];base=idx[r['question_id_sha256']]
            assert r['question_sha256']==c['question_sha256'] and r['paper_key']==c['paper_key']
            for plan in RETRIEVERS:
                v=r['retrievers'][plan];b=base['retrievers'][plan];keys=v['keys']
                assert keys==b['keys'] and len(keys)==len(set(keys)) and len(keys)<=20
                assert v['evidence_identity_sha256']==b['evidence_identity_sha256'] and v['winning_source_units']==b['winning_source_units']
                assert len(v['ranks'])==len(b['ranks']) and all(abs(a-bb)<=1e-10 for a,bb in zip(v['ranks'],b['ranks']))
                assert v['parent_metrics']==b['parent_metrics']==parent_metrics(c['gold_keys'],keys)
                rank=keys.index(c['paper_key'])+1 if c['paper_key'] in keys else None
                assert v['reciprocal_rank_at20']==b['reciprocal_rank_at20']==(1/rank if rank else 0)
                if plan=='best-unit':assert [u['key'] for u in v['winning_source_units']]==keys and all(type(u['sentence']) is int and u['sentence']>=-1 for u in v['winning_source_units'])
            formal+=1
    assert formal==3000
    build=read('build.json');assert build['full_original_source_bytewise_verified'] and build['memory_build']['indexed_records']==1000
    assert build['auxiliary_build']['papers']==1000 and build['auxiliary_build']['units']==4358
    assert build['auxiliary_build']['logical_file_bytes']==build['auxiliary_tree']['bytes']
    provenance=read('dataset-provenance.json');assert provenance['source_sha256']==SHA and provenance['context_items']==3358 and provenance['source_bytes']==len(raw)
    allrows=[r for t in trials for r in t['queries']]
    result={'instances':1000,'plans':{},'parent_pairs':{},'duplicate_normalized_body_groups':sum(n>1 for n in duplicates.values()),
        'records_in_duplicate_body_groups':sum(n for n in duplicates.values() if n>1),'Memory_bytes':build['storage']['logical_file_bytes'],
        'auxiliary_bytes':build['auxiliary_build']['logical_file_bytes'],'source_bytes_once':resources['total_bytes'],
        'peak_rss_bytes':dist(t['peak_rss_bytes'] for t in trials),'process_wall_s':dist(t['process_wall_including_startup_s'] for t in trials),
        'official_answer_accuracy':None,'evidence_coverage':None}
    for plan in RETRIEVERS:
        vals=[r['retrievers'][plan] for r in first];allvals=[r['retrievers'][plan] for r in allrows]
        result['plans'][plan]={'parent':{str(k):{'count':sum(v['parent_metrics'][str(k)]['gold_document_recall'] for v in vals),
            'recall':mean(v['parent_metrics'][str(k)]['gold_document_recall'] for v in vals)} for k in KS},
            'MRR_at20':mean(v['reciprocal_rank_at20'] for v in vals),'no_hits':sum(not v['keys'] for v in vals),
            'read_wall_s':dist(v['read_wall_s'] for v in allvals),'read_cpu_mean_s':mean(v['read_cpu_s'] for v in allvals),
            'counted_bytes':result['Memory_bytes']+result['source_bytes_once']+(result['auxiliary_bytes'] if plan=='best-unit' else 0)}
    for k in KS:
        key=str(k);result['parent_pairs'][key]=paired(first,lambda r:r['retrievers']['best-unit']['parent_metrics'][key]['gold_document_recall']-r['retrievers']['whole-paper']['parent_metrics'][key]['gold_document_recall'],papers=True)
    result['MRR_pair']=paired(first,lambda r:r['retrievers']['best-unit']['reciprocal_rank_at20']-r['retrievers']['whole-paper']['reciprocal_rank_at20'],papers=True)
    txt=log.read_text('utf-8');assert 'Ran 210 tests' in txt and 'OK (skipped=1)' in txt and 'FAILED' not in txt
    validation={'frozen_commit':frozen,'all_55_modules_protocol_and_driver_match_freeze':True,'formal_question_pairs':formal,'formal_read_operations':formal*2,
        'warmup_read_operations_excluded':6,'all_rounds_keys_ranks_identity_and_scores_equal':True,'all_1000_original_member_spans_and_projection_whitelist_independently_verified':True,
        'ranker_unchanged_from_v030':True,'actual_v030_reader_refuses_new_source':True,'original_file_and_persistent_trees_unchanged':True,
        'remote_model_calls':0,'official_answer_accuracy':None,'evidence_coverage':None,'cold_cache':None,'cross_machine':None,
        'tests':{'run':210,'passed':209,'skipped':1,'failed':0,'log_sha256':digest(log.read_bytes())}}
    save(root/'derived-metrics.json',result);save(root/'validation.json',validation);plot(root,result,len(raw));report(root,result,validation,provenance,resources,build)


def plot(root,result,original_bytes):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(11,4.7))
    for plan,color in zip(RETRIEVERS,('#496e9a','#26846f')):
        axes[0].plot(KS,[100*result['plans'][plan]['parent'][str(k)]['recall'] for k in KS],'-o',label=plan,color=color)
    axes[0].set_xticks(KS);axes[0].set_ylim(0,100);axes[0].set_xlabel('Top K unique papers');axes[0].set_ylabel('Exact target PMID recall (%)');axes[0].legend(fontsize=8);axes[0].grid(alpha=.2)
    bottom=[0.,0.]
    for label,values,color in (('Memory',[result['Memory_bytes']]*2,'#496e9a'),('All source once',[result['source_bytes_once']]*2,'#d0aa59'),('Auxiliary index',[0,result['auxiliary_bytes']],'#26846f')):
        ys=[v/1048576 for v in values];axes[1].bar([0,1],ys,bottom=bottom,label=label,color=color);bottom=[a+b for a,b in zip(bottom,ys)]
    axes[1].axhline(original_bytes/1048576,color='#666666',linestyle='--',label='Original JSON')
    axes[1].set_xticks([0,1],RETRIEVERS);axes[1].set_ylabel('Counted logical bytes (MiB)');axes[1].legend(fontsize=8)
    fig.suptitle('PubMedQA custom source-ID retrieval and counted storage; 1000 fixed questions')
    fig.tight_layout();fig.savefig(root/'pubmedqa-transfer.png',dpi=170);plt.close(fig)
    fig,ax=plt.subplots(figsize=(7,3.7));xs=list(range(len(KS)))
    vals=[100*result['parent_pairs'][str(k)]['instance_macro_delta'] for k in KS]
    lows=[v-100*result['parent_pairs'][str(k)]['unit_bootstrap_95_percent'][0] for k,v in zip(KS,vals)]
    highs=[100*result['parent_pairs'][str(k)]['unit_bootstrap_95_percent'][1]-v for k,v in zip(KS,vals)]
    ax.errorbar(xs,vals,yerr=[lows,highs],fmt='o',capsize=5,color='#26846f')
    ax.axhline(0,color='#666666',linestyle='--');ax.set_xticks(xs,[str(k) for k in KS]);ax.set_xlabel('Top K unique papers')
    ax.set_ylabel('Best-unit minus whole-paper recall (pp)');ax.set_title('Paired deltas with 1000-resample descriptive intervals');ax.grid(alpha=.2)
    fig.tight_layout();fig.savefig(root/'pubmedqa-paired-delta.png',dpi=170);plt.close(fig)


def report(root,r,v,p,resource,build):
    text='''# v0.31 实验报告：PubMedQA原始成员与冻结检索迁移

## 问题、来源与冻结边界

v0.30段落候选在QASPER改善、在SciFact退步且更贵。本轮将完全相同的候选迁移
到新来源PubMedQA PQA-L，不调权重、融合、窗口或默认。候选模块与v0.30逐字节
相同，whole-paper搜索/lookup/命中验证方法及STOP的AST相同；变化只在新增显式
来源reader与v4重绑定白名单，不将适配新输入称新检索算法。

'''
    text+=f"全部55模块/协议/驱动冻结`{v['frozen_commit']}`，210测试运行、209通过、1权限跳过。协议见[PUBMEDQA-TRANSFER](../../docs/PUBMEDQA-TRANSFER.md)，算法核对见algorithm-compatibility.json。\n\n"
    text+='''## 结论与决策

自定义PMID定位@1为957→950，@5为984→986，@10为990→988，@20为994→992。
@5仅净多2题（5赢/3输），描述区间跨零；MRR@20为0.970238→0.965823，配对区间
也跨零。没有支持稳定正迁移，不能用单个K的+2题称算法改进。与v0.30 SciFact退步
共同说明该单元粒度候选缺乏跨任务支配证据，保持显式、默认不换，不继续调gold权重。

候选额外1249639B，查询wall中位10.855→14.712ms。基线计入2152450B低于原JSON
2584787B（约少16.73%）；候选3402089B反而大约多31.62%。这只是当前实际账本，
共享运行时未全额分配，不能把基线数字称完整部署净压缩。候选未通过综合成本/
收益门槛，本轮新交付是可逆来源支持及透明迁移边界，无模型正确率结果。

后续保留现有词法默认作为离线基线，停止在这几套gold上追加融合/权重搜索。
工程优先回到路线中尚未完成的E2代码/数学字节表示候选，先冻结类型规则、计足
控制流/字典/解码器成本、再检验精确恢复和codec对照；E3及真实推理另需独立设计。

'''
    text+=f"固定[官方PubMedQA仓库](https://github.com/pubmedqa/pubmedqa)commit `{COMMIT}` 的[原始ori_pqal.json]({URL})，{p['source_bytes']}B、SHA256 `{SHA}`。仓库[LICENSE]({p['license_url']})原文可查，原科学数据不发布。\n\n"
    text+='''1000 PMID、1000唯一问题、3358 CONTEXTS条目，全部纳入。原任务给定context，
本项目人为改为在这1000篇中找来源：只评价精确目标PMID@K/MRR@20，不是官方
PubMedQA yes/no/maybe准确率、官方test/QA F1或科学结论正确率。其他命中的相关性
没有完整标注，不能计算通用precision。规则在本任务评分前固定，schema/范围
做过预检，不称严格盲测；近重复/同论文跨数据身份未全面验证。

## 原始字节、来源身份与标注隔离

新增显式*.pubmedqa.json类型，不改写原JSON。存储名ori_pqal.pubmedqa.json，
字节与原ori_pqal.json完全相同；每个原key/colon/value的offset/length/SHA保留。
独立核对1000原成员范围和投影：key=pubmedqa:PMID，title=PMID加原ID，正文严格
等于原CONTEXTS数组，不切句/修剪。文件没有独立文章标题，不能用QUESTION替代。
QUESTION/LONG_ANSWER/决策/预测/LABELS/MESHES/YEAR原字节留在CAS，但不进入FTS、
返回段落或模型上下文。合成marker测试两类检索及context payload均不泄漏这些字段。

v4显式加入新来源重绑定白名单，问句/注释/重排/改名变化仍绑定新原字节，原文
正文编辑必须更新投影；历史不能出现未来文本。原Memory v1–v4/CAS/归档格式不变，
来源类型需新reader。实际v0.30发行wheel按固定SHA在仓库外安装，lookup/search
对新来源均按QASPER schema错误拒绝，HEAD和持久树不变，不是模拟旧版错误。

'''
    text+=f"与既有数据的精确重叠统计：`{p['overlap']}`。本集自身规范化body重复组{r['duplicate_normalized_body_groups']}、涉及{r['records_in_duplicate_body_groups']}条。仅折叠空白并拼接数组条目，保留大小写/标点；不同ID空间或零精确匹配都不证明论文独立，近重复未测。\n\n"
    text+='''## 正式轮次与文档定位结果

三轮新进程、seed20261025+r打乱题序/条件；3000题对、6000读取、6预热排除。
重复轮次用于一致性/计时，不当3000独立论文。各轮keys/BM25/原文身份/MRR一致，
两检索器交集来源逐字段一致；起止原文件逐字节恢复，Memory和aux树大小/SHA不变。

![冻结迁移与完整计入空间](pubmedqa-transfer.png)

'''
    text+=table(['K','whole命中/1000','unit命中/1000','赢/输/平','差pp','PMID组bootstrap差区间pp'],[[k,*[int(r['plans'][plan]['parent'][str(k)]['count']) for plan in RETRIEVERS],f"{x['wins']}/{x['losses']}/{x['ties']}",f"{100*x['instance_macro_delta']:.3f}",f"[{100*x['unit_bootstrap_95_percent'][0]:.3f}, {100*x['unit_bootstrap_95_percent'][1]:.3f}]"] for k in KS for x in [r['parent_pairs'][str(k)]]])
    text+=f"\nMRR@20：whole {r['plans']['whole-paper']['MRR_at20']:.6f}，unit {r['plans']['best-unit']['MRR_at20']:.6f}；配对差{r['MRR_pair']['instance_macro_delta']:+.6f}，区间{r['MRR_pair']['unit_bootstrap_95_percent']}。\n"
    text+='\n每PMID仅1问题，按PMID/问题1000次bootstrap，seed20261025、排序索引24/974；仅描述本公开集，不代表独立重复科学研究或普遍因果。无命中数和全部原始记录见derived-metrics.json与round*.json；无QA/证据段落真值指标，保持null。\n'
    text+='\n![配对变化与描述区间](pubmedqa-paired-delta.png)\n'
    text+='\n## 构建、查询与存储成本\n\n'
    text+=table(['条件','计入总B','查询wall中位/p95 ms','CPU均值ms','MRR@20','无任何命中'],[[plan,x['counted_bytes'],f"{x['read_wall_s']['median']*1000:.3f}/{x['read_wall_s']['p95']*1000:.3f}",f"{x['read_cpu_mean_s']*1000:.3f}",f"{x['MRR_at20']:.6f}",x['no_hits']] for plan,x in r['plans'].items()])
    text+=f"\n原Memory {r['Memory_bytes']}B，aux(index+manifest){r['auxiliary_bytes']}B、4358单元，全部55模块/HTML一次{r['source_bytes_once']}B，新reader模块{resource['reader_module_bytes']}B单列。基线不收aux，候选全收；两条件同一实测代码安装均全计源。原JSON {p['source_bytes']}B，目录账本见build.json。\n"
    text+=f"\nMemory构建wall/CPU {build['build_wall_s']:.6f}/{build['build_cpu_s']:.6f}s；aux {build['auxiliary_build']['wall_including_checks_s']:.6f}/{build['auxiliary_build']['cpu_s']:.6f}s。整个worker RSS中位{r['peak_rss_bytes']['median']/1048576:.2f}MiB、全进程wall中位{r['process_wall_s']['median']:.3f}s。包含数据/标注/双条件/所有结果，不能分摊为某策略独立RAM。\n"
    text+='''
每查询含原Memory校验、aux整DB SHA（候选）、top20原记录重读/投影验证，不省略
完整性来换速度。bootstrap/独立评分不混入查询wall/CPU，CPU有计时分辨率0样本。
公共Python/SQLite/Zlib/OS、安装/pyc/文件系统未全额分配，计入总B不等于完整部署
成本；本任务pool规模/投影粒度与旧任务不同，不跨语料把绝对耗时称同任务加速。

## 安装核验范围更正与决策

v0.24–v0.30早期烟测用仓库内隔离安装目标、仓库外执行目录，原“仓库外安装”
表述不够准确。已全部补做物理上位于仓库之外的新wheel/对应native安装与外部
cwd复测，Release追加external-install-verification.json并回读SHA；旧tag/正式
观测/原核验记录保留。同Windows解释器和依赖，冷缓存/跨机器仍未测。新发布沿用
严格外部安装方式。更正不改变任何压缩/检索/模型结果。

本轮保持完整正负结果与默认，不以来源定位成功替代模型回答正确，不通过调参
改变迁移结论。具体收益和成本应按上表本任务判断；仍需要更大/独立任务、语义/
多跳和实际推理评测。新增真实模型预算未授权，模型调用0，答案与证据覆盖保持
null。E3神经压缩、长期会话、形式证明、冷缓存/跨机器/并发/掉电等均不由此证明。
'''
    (root/'SUMMARY.md').write_text(text,encoding='utf-8',newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('--input',type=Path,required=True);p.add_argument('--test-log',type=Path,required=True);p.add_argument('--frozen',required=True)
    a=p.parse_args();analyze(a.root,a.input,a.test_log,a.frozen)

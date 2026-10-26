"""Audit all text-frame restores and allocate control/source costs without overlap."""
import argparse
import json
from pathlib import Path
import subprocess

from rkv1.controlled import implementation_checksums
from rkv1.core import digest
from scripts.analyze_known_source import dist
from scripts.run_text_lanes import CODECS,MODES,INPUTS,inputs
from scripts.run_units import save
from scripts.summarize_units import table


def analyze(root,data,log,frozen):
    read=lambda n:json.loads((root/n).read_text('utf-8'))
    checks=read('source-checksums.json');assert checks==implementation_checksums() and len(checks)==57
    for name,sha in checks.items():assert digest(subprocess.check_output(['git','show',frozen+':rkv1/'+name]))==sha
    for rel in ('docs/TEXT-LANES.md','docs/text-lanes-inputs.json','scripts/run_text_lanes.py'):
        assert Path(rel).read_bytes()==subprocess.check_output(['git','show',frozen+':'+rel])
    resource=read('source-resource.json');assert resource['total_bytes']==sum(v['bytes'] for v in resource['files'].values())
    assert set(resource['files'])=={'rkv1/'+n for n in checks}|{'rkv1/memory_demo.html'}
    for name,v in resource['files'].items():assert Path(name).stat().st_size==v['bytes'] and digest(Path(name).read_bytes())==v['sha256']
    spec=read('dataset-provenance.json');assert spec==json.loads(INPUTS.read_text('utf-8'))
    rows=inputs(data);labels={r['id']:r for r in rows};science=[r['id'] for r in spec['files']]
    raw=read('trials.json');trials=raw['trials'];assert len(trials)==189 and raw['all_189_restores_bytewise_equal'] and raw['source_manifest_and_inputs_unchanged'] and raw['remote_model_calls']==0
    idx={(r['input_id'],r['codec'],r['mode'],r['round']):r for r in trials}
    assert set(idx)=={(r['id'],c,m,n) for r in rows for c in CODECS for m in MODES for n in range(3)}
    groups={};fsyncs=0
    for ident,r in labels.items():
        groups[ident]={'family':r['family'],'original_bytes':r['bytes'],'codecs':{}}
        for codec in CODECS:
            group={}
            for mode in MODES:
                items=[idx[(ident,codec,mode,n)] for n in range(3)];first=items[0]['stages']['pack'];info=first['encoder']
                for item in items:
                    p,d=item['stages']['pack'],item['stages']['restore']
                    assert p['phase']=='pack' and d['phase']=='restore' and p['frame_bytes']==d['frame_bytes']==first['frame_bytes']
                    assert p['frame_sha256']==d['frame_sha256']==first['frame_sha256'] and p['encoder']==info
                    assert p['input_sha256']==d['input_sha256']==r['sha256'] and d['bytewise_equal'] and d['restored_bytes']==r['bytes']
                    for stage in (p,d):
                        assert stage['remote_model_calls']==0 and stage['scientific_input_projects_not_imported'] and stage['file_fsync_count']==1
                        assert stage['input_id']==ident and stage['round']==item['round'] and stage['codec']==codec and stage['mode']==mode;fsyncs+=1
                    assert info['codec']==codec and info['requested_mode']==mode and info['original_bytes']==r['bytes']
                    assert info['frame_header_bytes']==66 and info['dictionary_bytes']==info['model_bytes']==0
                    assert [a['mode'] for a in info['attempts']]==(['plain','lanes'] if mode=='auto' else [mode])
                    for a in info['attempts']:
                        assert a['frame_bytes']==66+a['compressed_payload_bytes']
                        if a['mode']=='lanes':
                            s=a['lanes'];assert s['transform_header_bytes']==40 and sum(s['pool_bytes'])==r['bytes']
                            assert 2*s['tokens']<=s['control_bytes']<=2*r['bytes']
                            assert s['transformed_bytes']==a['transformed_bytes']==40+s['control_bytes']+r['bytes']
                        else:assert a['lanes'] is None and a['transformed_bytes']==r['bytes']
                src=resource['common_text_frame_source_bytes']+(resource['candidate_text_lanes_source_bytes'] if mode!='plain' else 0)
                group[mode]={'frame_bytes':first['frame_bytes'],'frame_sha256':first['frame_sha256'],'selected_mode':info['selected_mode'],
                    'encoder_attempts':info['attempts'],'dedicated_source_bytes':src,'dedicated_net_bytes':first['frame_bytes']+src,
                    'full_RKV_source_net_bytes':first['frame_bytes']+resource['total_bytes'],
                    'encode_compute_wall_s':dist(x['stages']['pack']['compute']['wall_s'] for x in items),
                    'decode_compute_wall_s':dist(x['stages']['restore']['compute']['wall_s'] for x in items),
                    'pack_phase_excluding_source_load_wall_s':dist(x['stages']['pack']['phase_wall_excluding_source_load']['wall_s'] for x in items),
                    'restore_phase_excluding_truth_and_audit_wall_s':dist(x['stages']['restore']['phase_wall_excluding_truth_load_and_audit']['wall_s'] for x in items),
                    'pack_source_load_wall_s':dist(x['stages']['pack']['source_load']['wall_s'] for x in items),
                    'encode_CPU_s':dist(x['stages']['pack']['compute']['cpu_s'] for x in items),'decode_CPU_s':dist(x['stages']['restore']['compute']['cpu_s'] for x in items),
                    'encode_process_wall_s':dist(x['stages']['pack']['process_wall_including_startup_s'] for x in items),
                    'decode_process_wall_s':dist(x['stages']['restore']['process_wall_including_startup_s'] for x in items),
                    'pack_peak_rss_bytes':dist(x['stages']['pack']['peak_rss_bytes'] for x in items),
                    'restore_peak_rss_bytes':dist(x['stages']['restore']['peak_rss_bytes'] for x in items),
                    'codec_preloaded_pack':items[0]['stages']['pack']['codec_preloaded_before_phase'],
                    'codec_preloaded_restore':items[0]['stages']['restore']['codec_preloaded_before_phase']}
            for mode in ('lanes','auto'):
                b,v=group['plain'],group[mode]
                v['net_space_pass']=v['dedicated_net_bytes']<b['dedicated_net_bytes']
                v['encode_median_not_slower']=v['encode_compute_wall_s']['median']<=b['encode_compute_wall_s']['median']
                v['decode_median_not_slower']=v['decode_compute_wall_s']['median']<=b['decode_compute_wall_s']['median']
                v['joint_pass']=v['net_space_pass'] and v['encode_median_not_slower'] and v['decode_median_not_slower']
                v['paired_encode_wall_ratio_samples']=[idx[(ident,codec,mode,n)]['stages']['pack']['compute']['wall_s']/idx[(ident,codec,'plain',n)]['stages']['pack']['compute']['wall_s'] for n in range(3)]
                v['paired_decode_wall_ratio_samples']=[idx[(ident,codec,mode,n)]['stages']['restore']['compute']['wall_s']/idx[(ident,codec,'plain',n)]['stages']['restore']['compute']['wall_s'] for n in range(3)]
            auto=group['auto'];assert auto['frame_bytes']<=group['plain']['frame_bytes']
            assert auto['frame_sha256']==group[auto['selected_mode']]['frame_sha256']
            groups[ident]['codecs'][codec]=group
    assert fsyncs==378
    corpus={}
    for codec in CODECS:
        corpus[codec]={}
        for mode in MODES:
            frame=sum(groups[i]['codecs'][codec][mode]['frame_bytes'] for i in science)
            source=resource['common_text_frame_source_bytes']+(resource['candidate_text_lanes_source_bytes'] if mode!='plain' else 0)
            corpus[codec][mode]={'science_files':6,'original_bytes':sum(labels[i]['bytes'] for i in science),'frame_bytes_sum':frame,
                'dedicated_source_once_bytes':source,'dedicated_net_bytes':frame+source,'full_RKV_source_net_bytes':frame+resource['total_bytes']}
    result={'inputs':groups,'fixed_scientific_corpus_shared_once':corpus,
        'scientific_candidate_points':36,'scientific_joint_passes':sum(groups[i]['codecs'][c][m]['joint_pass'] for i in science for c in CODECS for m in ('lanes','auto')),
        'noise_joint_passes':sum(groups[spec['negative_control']['id']]['codecs'][c][m]['joint_pass'] for c in CODECS for m in ('lanes','auto')),
        'scientific_net_space_passes':sum(groups[i]['codecs'][c][m]['net_space_pass'] for i in science for c in CODECS for m in ('lanes','auto'))}
    txt=log.read_text('utf-8');assert 'Ran 218 tests' in txt and 'OK (skipped=1)' in txt and 'FAILED' not in txt
    validation={'frozen_commit':frozen,'all_57_modules_protocol_driver_and_inputs_manifest_match_freeze':True,'formal_encode_restore_pairs':189,'fresh_subprocess_stages':378,
        'actual_file_fsyncs':378,'all_189_restores_bytewise_and_SHA_equal':True,'all_rounds_frames_choices_and_control_accounts_identical':True,
        'source_files_and_protocol_unchanged':True,'no_input_project_import_or_execution':True,'remote_model_calls':0,'inference_quality':None,'cold_cache':None,'cross_machine':None,
        'tests':{'run':218,'passed':217,'skipped':1,'failed':0,'log_sha256':digest(log.read_bytes())}}
    save(root/'derived-metrics.json',result);save(root/'validation.json',validation);plot(root,result,spec);report(root,result,validation,spec,resource)


def plot(root,r,spec):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    labels=[x['id'] for x in spec['files']]+[spec['negative_control']['id']]
    names=['SciPy\nlinprog','SciPy\nbasic','SymPy\nexpr','SymPy\nintegrals','LaTeX\namsmath','LaTeX\nltmath','Synthetic\nnoise']
    fig,axes=plt.subplots(1,3,figsize=(14,4.3),sharey=True)
    for ax,codec in zip(axes,CODECS):
        for mode,color in (('lanes','#26846f'),('auto','#ba7840')):
            ax.plot(range(7),[100*r['inputs'][i]['codecs'][codec][mode]['dedicated_net_bytes']/r['inputs'][i]['codecs'][codec]['plain']['dedicated_net_bytes'] for i in labels],'-o',label=mode,color=color)
        ax.axhline(100,color='#666666',linestyle='--');ax.set_xticks(range(7),names,fontsize=7);ax.set_title(codec);ax.grid(alpha=.2);ax.legend(fontsize=8)
    axes[0].set_ylabel('Frame + dedicated-source cost / plain (%)')
    fig.suptitle('Frozen lexical byte lanes: same codec, full frame/control and dedicated source allocation')
    fig.tight_layout();fig.savefig(root/'text-lanes-net-cost.png',dpi=170);plt.close(fig)


def report(root,r,v,spec,resource):
    text='''# v0.32 实验报告：代码/数学词法字节通道的完整成本

## 冻结问题与方法

E2代码/数学表示仍有空缺。本轮只测一个原始字节重排：ASCII标识符、十进制
拼写、ASCII空白和其他字节四通道，control逐token记类型与canonical长度。
不执行输入代码，不做AST/表达式等价化，所有原字节(含注释/字符串/CRLF/Unicode)
都保存。类型是字节词法，不是完整语言tokenizer或语义压缩。

独立RKVTEXT1实验帧66B header，原样/通道共享同一框架、原SHA/长度及单codec流。
通道输入为40B长度头+control+四pool，全部再压缩。对Zlib6/Zstd3/LZMA6分别测
plain/lanes/auto，auto实际计算两者并选完整帧较小者、同分plain，双尝试全部收费。
不是主RKV归档v7，不改变旧Archive/Memory/CAS，也不产生随机范围读/推理收益。

'''
    text+=f"全部57模块/驱动/协议/输入清单冻结`{v['frozen_commit']}`；218测试运行、217通过、1权限跳过。格式/边界/门槛见[TEXT-LANES](../../docs/TEXT-LANES.md)。\n\n"
    text+='## 结论及架构决策\n\n'
    text+=f"科学候选净空间{r['scientific_net_space_passes']}/36、联合{r['scientific_joint_passes']}/36通过；噪声联合{r['noise_joint_passes']}/6。所有189次实际恢复正确，但正确性不等于压缩收益。\n\n"
    for codec,modes in r['fixed_scientific_corpus_shared_once'].items():
        b=modes['plain']['dedicated_net_bytes'];n=modes['lanes']['dedicated_net_bytes'];a=modes['auto']['dedicated_net_bytes']
        text+=f"- {codec}六科学文件共享专用源一次：plain {b}B，lanes {n}B（增{100*(n/b-1):.2f}%），auto {a}B。\n"
    text+='''
自动模式21/21个输入/codec条件都回退plain（含噪声；三轮共63正式auto编码），
帧字节与plain完全相同，而双尝试/变换成本和候选源码仍收费。强制lanes连不计
源码的帧也更大，不能把问题解释为只需摊薄decoder。结果否定当前四通道表示
在这些工作点的优势，不否定所有代码/数学表示；没有分离control与跨类统计损失
的消融，不能将失败精确归因给某一原因。

当前格式的输出比特数不因搬到Rust而改变，还要增加实际库成本，因此不追加该
表示的原生化/主格式集成，默认继续普通codec。后续回到动态证据记忆工程缺口，
优先冻结一个单writer/多reader快照一致性实验；它属于机械正确性验证，不当作
生产并发、模型推理或长期会话收益。E3神经预测仍需独立设计和完整模型成本。

'''
    text+='## 数据与可复现范围\n\n'
    text+=table(['家族','固定ref','原路径','原字节B'],[[x['family'],x['ref'],x['source_path'],x['bytes']] for x in spec['files']])
    text+='''
六文件来自SciPy/SymPy/LaTeX2e三个项目，不当六个独立科学领域或抽样总体；版本
是固定历史基准而非最新软件推荐。原commit/SHA256/Git blob SHA/官方URL/许可证
见dataset-provenance.json，源代码和可逆帧/恢复文件不发布。另262144B固定SHAKE
噪声仅作负对照，不当真实科学来源。没有在看压缩率后挑文件、级别、类规则或扩大N。

189编码/恢复对、378个独立新进程阶段、378次实际文件fsync；无warmup。全部恢复
逐字节与原SHA相等，三轮每条件帧SHA/大小/选择/control账本全同，源/协议不变。
每阶段记录codec是否已由公共模块预载；首次lazy导入若发生在计算中则收费，
整个进程wall/RSS也列出。不把codec已预载说成首次导入，冷缓存/跨机器未测。

## 成本口径及联合门槛

A为实际完整帧66+compressed payload；40+control+pool是压缩前结构，不在A上
再次加一遍。B为A加专用帧模块源码(含编/解码)，候选再加通道模块正/反变换；
C为A加实际整个RKV57模块/HTML一次。B/C是替代场景，不能叠加重复计源。
codec/Python/OS/安装/pyc/文件系统未全额分配，任何场景都不是完整部署成本。

每单文件各自全收B，若严格净省且三轮纯encode/decode wall中位都不慢才联合
通过；六科学文件固定N=6共享源码一次另报空间，不混噪声、不当所有单文件通过。
重复轮只是相同输入计时，不当独立样本或统计因果证明。全部原样本在trials.json。

'''
    text+=f"公共帧模块{resource['common_text_frame_source_bytes']}B、候选通道模块{resource['candidate_text_lanes_source_bytes']}B、整个RKV源{resource['total_bytes']}B。字典/模型/本实验专属原生库0B；已安装codec实现成本仍是未全额分配的公共部分。\n\n"
    text+='## 逐输入完整帧/源成本与联合结果\n\n![净成本比](text-lanes-net-cost.png)\n\n'
    text+=table(['输入','codec','条件/实际选择','A帧B','B帧+专用源B','空间通过','编码中位ms','解码中位ms','联合'],[
        [i,c,m+'/'+x['selected_mode'],x['frame_bytes'],x['dedicated_net_bytes'],x.get('net_space_pass','baseline'),f"{x['encode_compute_wall_s']['median']*1000:.3f}",f"{x['decode_compute_wall_s']['median']*1000:.3f}",x.get('joint_pass','baseline')]
        for i,g in r['inputs'].items() for c,modes in g['codecs'].items() for m,x in modes.items()])
    text+=f"\n六科学输入候选工作点36个，专用源净空间通过{r['scientific_net_space_passes']}/36、联合通过{r['scientific_joint_passes']}/36；噪声6点联合{r['noise_joint_passes']}/6。门槛不因结果而调整。\n"
    text+='\n## 固定六文件共享源一次的空间情景\n\n'
    text+=table(['codec','条件','原科学字节B','完整帧合计B','共享专用源后B','全部RKV源后B'],[[c,m,x['original_bytes'],x['frame_bytes_sum'],x['dedicated_net_bytes'],x['full_RKV_source_net_bytes']] for c,modes in r['fixed_scientific_corpus_shared_once'].items() for m,x in modes.items()])
    text+='\n这是明确N=6的空间账本，不把六次冷进程导入/写盘相加称单个部署批处理耗时，也不扩大对象数摊薄decoder获得正结果。B与C不相加。\n'
    text+='\n## 控制/回退、I/O与资源\n\n'
    text+='''每个attempt原长度、变换长度、tokens/control长度、四pool长度、40B结构头、
compressed payload和66B帧头均在原始JSON。auto回退plain也收费变换和两次codec，
并在B分配候选源码；实际帧可以等于plain，不能因此声称编码/部署成本免费。

pack source_load含输入pin SHA/读取，纯encode(含原SHA)、帧写入/flush/fsync分别
测；pack phase排除source_load。restore真值读取是独立基准前提，不属于实际
decoder；真实phase含帧读取、decode(含原SHA)、恢复写入fsync，逐字节读回审计
另计。不能把纯encode/decode当完整pack/restore或省略新codec首次导入。每阶段
新进程，实际模块预载状态、CPU样本、进程wall和峰值RSS完整留存。RSS包含输入/
真值/输出/元数据/公共模块，不能解释为codec独占RAM。没有目录fsync/掉电证明。

'''
    text+=table(['输入','codec','条件','pack阶段中位ms','restore阶段中位ms','encode/restore进程RSS中位MiB'],[[i,c,m,f"{x['pack_phase_excluding_source_load_wall_s']['median']*1000:.3f}",f"{x['restore_phase_excluding_truth_and_audit_wall_s']['median']*1000:.3f}",f"{x['pack_peak_rss_bytes']['median']/1048576:.2f}/{x['restore_peak_rss_bytes']['median']/1048576:.2f}"] for i,g in r['inputs'].items() for c,modes in g['codecs'].items() for m,x in modes.items()])
    text+='''
## 格式拒绝、决策与后续

测试拒绝未知magic/codec/method、错长度/SHA、非canonical或越界/未耗尽通道、
压缩后额外字节/串接流及伪造小长度解压；Zstd要求声明内容长度/受限window/无
外部字典，LZMA memlimit256MiB。原样与通道均做原SHA验证。实验帧由主Archive
明确拒绝，旧v1–v6归档及所有旧来源/默认仍经回归，不把新prototype当生产格式。

保留全部负结果和对象/codec适用范围；默认不集成。只有明确净空间、真实热点及
包含完整原生库成本的工作负载才考虑Rust，不从Python慢推导综合收益。本轮没有
模型/检索/推理收益，远程模型调用0；E3神经预测、语义压缩、多跳、长期会话、
形式证明、冷缓存/跨机器/并发/掉电等未测。具体后续应依据上述门槛，不在既有
语料调规则/级别或改变对象数追求正结果。
'''
    (root/'SUMMARY.md').write_text(text,encoding='utf-8',newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('--data',type=Path,required=True);p.add_argument('--test-log',type=Path,required=True);p.add_argument('--frozen',required=True)
    a=p.parse_args();analyze(a.root,a.data,a.test_log,a.frozen)

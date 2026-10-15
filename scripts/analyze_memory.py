"""Audit raw retrieval/API records without new model calls or tuning."""
import argparse
import hashlib
import json
from pathlib import Path
import re

from rkv1.benchmark import summary
from rkv1.controlled import implementation_checksums
from rkv1.memory import Memory,_json
from rkv1.memory_model import messages,exposed_hits,validate_answer
from scripts.run_memory import inputs,api_plan,score
from scripts.run_units import save
from scripts.summarize_units import table


def analyze(root,work,test_log):
    read=lambda n:json.loads((root/n).read_text("utf-8"))
    checks=read("source-checksums.json");assert checks==implementation_checksums()
    _,claims=inputs();claim_map={c["id"]:c for c in claims}
    retrieval=read("retrieval.json");rjournal=[json.loads(x) for x in (root/"retrieval-journal.jsonl").read_text("utf-8").splitlines()]
    assert retrieval["trials"]==rjournal and len(rjournal)==564
    expected={c["id"] for c in claims if c["evidence"]};assert len(expected)==188
    keys={};latencies=[]
    for n in range(3):assert len([r["claim_id"] for r in rjournal if r["round"]==n])==188 and {r["claim_id"] for r in rjournal if r["round"]==n}==expected
    for r in rjournal:
        c=claim_map[r["claim_id"]];gold_keys={"doc:"+str(k) for k in c["evidence"]}
        assert r["gold_keys"]==sorted(gold_keys) and r["question_sha256"]==hashlib.sha256(c["claim"].encode()).hexdigest()
        assert keys.setdefault(c["id"],r["keys"])==r["keys"] and r["source_bytes_verified"]
        for k in (1,5,10):
            assert r["metrics"][str(k)]=={"gold_document_recall":len(gold_keys&set(r["keys"][:k]))/len(gold_keys),"any_gold_hit":bool(gold_keys&set(r["keys"][:k]))}
        latencies.append(r["wall_s"])
    assert retrieval["wall_s"]==summary(latencies)
    first=[r for r in rjournal if r["round"]==0]
    metrics={str(k):{"macro_gold_document_recall":sum(r["metrics"][str(k)]["gold_document_recall"] for r in first)/188,
                    "claims_with_any_gold":sum(r["metrics"][str(k)]["any_gold_hit"] for r in first)} for k in (1,5,10)}
    assert metrics==retrieval["metrics"]
    model=read("model-eval.json");journal=[json.loads(x) for x in (root/"api-journal.jsonl").read_text("utf-8").splitlines()]
    assert model["records"]==journal and len(journal)==24 and model["complete"]
    plan=api_plan(claims);assert [(r["claim_id"],r["record"]["retrieval_enabled"]) for r in journal]==[(c["id"],enabled) for c,enabled in plan]
    memory=Memory(work/"memory");total_usage={k:0 for k in ("prompt_tokens","completion_tokens","total_tokens","prompt_cache_hit_tokens","prompt_cache_miss_tokens")}
    conditions={};failures=[];pairs={}
    for r in journal:
        record=r["record"];c=claim_map[r["claim_id"]];enabled=record["retrieval_enabled"]
        assert r["score"]==score(c,record) and record["api_calls"]==1 and record["max_tokens"]==256
        assert record["model"]=="deepseek-flash" and record["request_extra_body"]=={"thinking":{"type":"disabled"},"response_format":{"type":"json_object"}}
        result=memory.search(c["claim"],snapshot=record["snapshot_id"],top_k=5) if enabled else {"hits":[]}
        visible=exposed_hits(result["hits"])
        assert record["retrieved_keys"]==[h["key"] for h in result["hits"]]
        assert record["exposed_sentences"]=={h["key"]:h["visible_sentence_ids"] for h in visible}
        payload={"model":record["model"],"messages":messages(c["claim"],visible),"temperature":0,"max_tokens":256,**record["request_extra_body"]}
        raw=json.dumps(payload,ensure_ascii=False,separators=(",",":")).encode()
        assert hashlib.sha256(raw).hexdigest()==record["prompt_sha256"]
        if record["accepted"]:assert record["answer"]==validate_answer(record["raw_model_content"],visible)
        data={k:v for k,v in record.items() if k!="writeback"};data={**data,"record_type":"derived-model-answer","primary_evidence":False}
        raw=_json(data);key=hashlib.sha256(raw).hexdigest()
        assert key==record["writeback"]["answer_id"] and (work/"memory/answers"/(key+".json")).read_bytes()==raw
        usage=record["usage"];assert usage and usage["completion_tokens"]<=256 and usage["total_tokens"]==usage["prompt_tokens"]+usage["completion_tokens"]
        for k in total_usage:total_usage[k]+=usage[k]
        pairs.setdefault(c["id"],{})[enabled]=r["score"]["grounded_correct"]
        if enabled and not r["score"]["grounded_correct"]:
            failures.append({"claim_id":c["id"],"gold_verdict":r["score"]["gold_verdict"],"model_verdict":record["answer"]["verdict"] if record["answer"] else None,
                "gold_document_in_top5":bool(set(record["retrieved_keys"])&{"doc:"+str(k) for k in c["evidence"]}),
                "complete_gold_rationale_exposed":any(all(i in record["exposed_sentences"].get("doc:"+str(doc),[]) for i in rationale["sentences"]) for doc,rs in c["evidence"].items() for rationale in rs),
                "complete_gold_rationale_cited":r["score"]["complete_gold_rationale_cited"]})
    for enabled,name in ((False,"empty_evidence"),(True,"retrieved_evidence")):
        xs=[r for r in journal if r["record"]["retrieval_enabled"]==enabled];labelled=[r for r in xs if r["score"]["gold_verdict"]!="INSUFFICIENT"]
        conditions[name]={"samples":len(xs),"schema_and_citation_binding_valid":sum(r["record"]["accepted"] for r in xs),
             "gold_verdict_correct":sum(r["score"]["verdict_correct"] for r in xs),"grounded_correct":sum(r["score"]["grounded_correct"] for r in xs),
             "annotated_evidence_claims":len(labelled),"complete_gold_rationale_cited":sum(r["score"]["complete_gold_rationale_cited"] for r in labelled),
             "verdict_and_complete_rationale_correct":sum(r["score"]["grounded_correct"] for r in labelled),
             "model_wall_s":summary([r["record"]["model_wall_s"] for r in xs])}
    paired={"retrieval_only_correct":sum(v[True] and not v[False] for v in pairs.values()),"empty_only_correct":sum(v[False] and not v[True] for v in pairs.values()),
            "both_correct":sum(v[False] and v[True] for v in pairs.values()),"neither_correct":sum(not v[False] and not v[True] for v in pairs.values())}
    resources=read("resources.json");before=read("build.json")["storage_before_queries"];after=resources["all_retained_after_update"]
    assert after==memory.stats();mechanics=read("mechanics.json")
    assert all(mechanics[k] for k in ("new_note_bytewise_verified","fresh_process_object_reopen_retrieves_update","old_snapshot_excludes_future_note","derived_output_not_primary_or_retrievable"))
    ui=Path("rkv1/memory_demo.html").read_bytes()
    result={"retrieval_metrics":metrics,"retrieval_wall_s":retrieval["wall_s"],"model_conditions":conditions,"paired_grounded_outcomes":paired,
        "model_failures":failures,"provider_reported_token_usage":total_usage,"generation_calls":24,"billed_cost_usd":None,
        "resources":{"before_queries":before,"all_retained_after_update":after,"original_corpus_bytes":8307875,
          "initial_store_plus_index_div_original":before["logical_file_bytes"]/8307875,"all_retained_div_original":after["logical_file_bytes"]/8307875,
          "model_weights_remote_runtime_bytes":None,"common_runtime_allocation_complete":False},
        "ui_asset":{"path":"rkv1/memory_demo.html","bytes":len(ui),"sha256":hashlib.sha256(ui).hexdigest()}}
    raw=test_log.read_bytes();log=raw.decode("utf-8-sig");ran=re.search(r"Ran (\d+) tests",log);ok=re.search(r"^OK(?: \(skipped=(\d+)\))?\r?$",log,re.M)
    assert ran and ok and "FAILED (" not in log
    validation={"frozen_python_sources_verified":len(checks),"all_retrieval_records_match_append_journal":564,"unique_annotated_claims":188,
       "original_record_hashes_and_index_bindings_verified":True,"retrieval_ranking_stable_across_three_rounds":True,
       "real_API_calls":24,"planned_API_order_and_no_retries_verified":True,"all_24_request_hashes_reconstructed_without_keys":True,
       "all_derived_answer_records_reconstructed_and_not_primary":True,"all_scores_recomputed_from_pinned_annotations":True,
       "model_scientific_entailment_proof":False,"tests":{"run":int(ran[1]),"passed":int(ran[1])-int(ok[1] or 0),"skipped":int(ok[1] or 0),"failed":0,"log_sha256":hashlib.sha256(raw).hexdigest()},
       "cold_cache":None,"cross_machine":None,"long_conversation":None,"multi_hop":None,"formal_proof":None,"neural_compression":None}
    text="""# v0.15.0 首个证据记忆与模型回答基线

本轮打通原始资料CAS入库、SQLite BM25词法检索、原记录读取和SHA校验、真实模型API
判断、句子引用绑定、派生回答写回；新增来源后可读新/旧快照。E4最小基线，不是
embedding/图检索、自动学习、多轮对话、多跳或形式化证明；E3仍未实施。

SciFact固定corpus.jsonl 5,183摘要，8,307,875B；索引不含claims或gold标签。188条
有标注主张，三轮各188次，共564次top10检索，逐条原记录验证；重复轮次不是独立
样本。原JSON转义/换行和完整源文件字节保留。时间含整个索引SHA与CAS命中记录校验。

"""
    text+=table(["k","宏平均gold文档召回","至少命中一份gold主张数"],[[k,f"{100*metrics[str(k)]['macro_gold_document_recall']:.2f}%",f"{metrics[str(k)]['claims_with_any_gold']}/188"] for k in (1,5,10)])
    text+=f"\n本机温缓存检索中位 {retrieval['wall_s']['median']*1000:.2f} ms，p95 {retrieval['wall_s']['p95']*1000:.2f} ms。dev公开数据、单机描述统计，不是跨语言语义召回或严格盲测。\n\n"
    text+="模型为用户指定DeepSeek deepseek-flash官方API，thinking关闭、JSON输出、temperature0、每请求max_tokens256。资料/检索本机CPU，模型远程计算。12条预定平衡主张×两条件，共24次生成，随机顺序、无重试；模型可能见过公开数据，别名与远程权重不可独立冻结。\n\n"
    text+=table(["条件","格式/引用绑定有效","标注判定正确","8条有证据主张完整gold依据","8条判定和依据同时正确"],
       [[name,f"{v['schema_and_citation_binding_valid']}/12",f"{v['gold_verdict_correct']}/12",f"{v['complete_gold_rationale_cited']}/8",f"{v['verdict_and_complete_rationale_correct']}/8"] for name,v in conditions.items()])
    text+="\n空证据仍受只据所给证据回答的提示约束，不是无约束闭卷模型或成熟RAG基线。INSUFFICIENT的4条按数据标注评分，不证明全库无证据；引用绑定通过不证明科学蕴含。\n\n"
    text+=f"配对：仅检索条件正确 {paired['retrieval_only_correct']} 条，仅空证据正确 {paired['empty_only_correct']} 条，两者都正确 {paired['both_correct']} 条，两者都错 {paired['neither_correct']} 条。不据12条单次样本宣称普遍提升。\n\n"
    text+=table(["未正确主张ID","gold","模型","gold在top5","引用完整gold依据"],[[x['claim_id'],x['gold_verdict'],x['model_verdict'],x['gold_document_in_top5'],x['complete_gold_rationale_cited']] for x in failures])
    text+="\n两条失败主张的gold文档都在top5，且完整gold依据均已提供给模型。主张3弃答且未引用；主张48引用完整依据后仍判证据不足。本样本的两次失败不能归因于漏召回或上下文截断；后续区分判定/弃答与引用选择，不改变已测提示或筛掉失败。\n\n"
    text+=f"服务reported tokens：输入 {total_usage['prompt_tokens']:,}，输出 {total_usage['completion_tokens']:,}，合计 {total_usage['total_tokens']:,}；输入缓存命中 {total_usage['prompt_cache_hit_tokens']:,}。账单费用未知，模型权重/远程运行时成本未知；不以token量冒充实际扣费。\n\n"
    text+=f"## 资源与机制边界\n\n初始CAS+索引/清单/HEAD共 {before['logical_file_bytes']:,} B，为原文 {before['logical_file_bytes']/8307875:.3f}×；保留两个完整索引快照及派生记录后 {after['logical_file_bytes']:,} B（其中索引 {after['by_directory_bytes']['indexes']:,} B），为原文 {after['logical_file_bytes']/8307875:.3f}×。完整列明本地文件，不称总系统净压缩收益；公共运行时、文件系统元数据、远程模型成本未完整分配。\n\n"
    text+="更新检查使用单独合成UTF-8/CRLF记录，新建Memory实例可召回新记录，旧快照不可读取未来记录；合成派生探针不进入原始证据索引。真实24个模型回答均单独写回并核对身份。该机制不等于长期连续对话记忆、自动整理、冲突消解或模型自主写证据。\n\n"
    text+="文件同步/索引发布仍为研究原型边界，未验证目录/卷或真实掉电。原始语料、密钥和完整摘要提示词副本不进入发行包；结果保留请求SHA、来源定位、模型原响应和usage。后续优先区分检索漏召回、模型弃答/判定与索引成本，再扩独立问题与长会话；不更改已测样本或门槛。\n"
    save(root/"derived-metrics.json",result);save(root/"validation.json",validation)
    with (root/"SUMMARY.md").open("x",encoding="utf-8",newline="\n") as f:f.write(text)
    return result


def plot(root,result):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(11,4.4),layout="constrained")
    values=[100*result["retrieval_metrics"][str(k)]["macro_gold_document_recall"] for k in (1,5,10)]
    bars=axes[0].bar(['@1','@5','@10'],values,color='#238066');axes[0].bar_label(bars,fmt='%.2f%%',padding=3)
    axes[0].set_ylim(0,105);axes[0].set_ylabel('Macro annotated-document recall (%)');axes[0].set_title('BM25: 188 unique annotated dev claims')
    values=[result["model_conditions"][c]["gold_verdict_correct"] for c in ('empty_evidence','retrieved_evidence')]
    bars=axes[1].bar(['Empty evidence','Retrieved evidence'],values,color=['#64748b','#238066']);axes[1].bar_label(bars,fmt='%d / 12',padding=3)
    axes[1].set_ylim(0,13);axes[1].set_ylabel('Gold verdicts correct');axes[1].set_title('Same evidence-only responder, 12 fixed claims')
    for ax in axes:ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
    fig.suptitle('v0.15 evidence memory baseline\nPublic dev data; small paired API sample, no general reasoning claim')
    target=root/'memory-baseline.png'
    if target.exists():raise ValueError('Plot exists')
    fig.savefig(target,dpi=160);plt.close(fig)


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('--work',type=Path,default=Path('.tools/memory-v015-demo'))
    p.add_argument('--test-log',type=Path,required=True);p.add_argument('--plot',action='store_true');args=p.parse_args()
    result=analyze(args.root,args.work,args.test_log)
    if args.plot:plot(args.root,result)

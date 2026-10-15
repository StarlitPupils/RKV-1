"""Audit raw v6 records and apply the preregistered engineering acceptance gate."""
import argparse
import hashlib
import json
from pathlib import Path
import re

from rkv1.controlled import implementation_checksums,inventory
from rkv1.layout_benchmark import matrix
from rkv1.layout_data import SPECS as NEW_SPECS
from rkv1.scientific_data import SPECS as OLD_SPECS
from rkv1.numeric_data import SPECS as NUMERIC_SPECS
from scripts.run_layout import sources
from scripts.run_units import save
from scripts.summarize_numeric import paired
from scripts.summarize_units import table,p95

DATASETS=("spitzer32","m13_64","rosat32","ecg","noise")
METHODS=("ordinary","global-shuffle","typed-fixed","segmented-none","typed-segmented")


def label(r):
    c=r["configuration"];return f"{c['compression']}/{c['chunk_size']//1024}KiB/{c['method']}"


def analyze(root,test_log):
    read=lambda p:json.loads((root/p).read_text("utf-8"))
    checks=read("source-checksums.json");assert checks==implementation_checksums()
    resource=read("dedicated-resources.json");assert resource["sources"]==sources()
    sizes={s["name"]:s["bytes"] for s in resource["sources"]}
    charges={"ordinary":0,"global-shuffle":sizes["numeric.py"],"typed-fixed":sum(sizes.values()),
             "segmented-none":sizes["layouts.py"],"typed-segmented":sum(sizes.values())}
    result={"allocated_once_bytes":charges,"resources":resource,"datasets":{}}
    totals={k:0 for k in ("formal_roundtrips","warmup_roundtrips","formal_range_reads","warmup_range_reads")}
    audit={}
    text="""# v0.12.0 FITS 类型分流与区域分块

规则/矩阵/验收在新验证输入压缩结果之前固定，见 docs/LAYOUT.md（协议提交38473b2）。
Spitzer为已见开发记录；M13 float64与ROSAT float32为新增验证记录。
它们仍是同一托管项目的天文示例，不称跨领域或严格盲测。ECG和噪声为未识别格式对照。
所有原文件头/数据/填充原样恢复，不解析或重写数值。规则只识别完整单一2D浮点主图像。

每组20条件：Zlib6/Zstd3 ×64KiB/1MiB ×五种方法，全同v6。
普通固定块；整文件字节重排；固定块仅对完全位于图像中的块重排；仅分段；分段且仅图像重排。
全量归档计prefix/JSON/路径/块/文件SHA与实际配方；分段读取器另建前缀偏移数组，逻辑字节和RSS分别报告。
候选分配完整layouts.py一次，配置数值策略另分配完整numeric.py一次，包括未识别格式回退。
公共Python/core/Zstd和pyc未全额分配，不称完整部署成本；无专用DLL/模型/字典。

一次完整预热+五轮正式，条件/轮次打乱；分阶段新进程测wall/CPU/RSS，范围请求跨条件/模式匹配。
本机温OS缓存；重开读取器不是冷磁盘。p95指各轮p95的中位，配对速度是逐轮baseline/candidate再取中位。
持久性口径：归档编码flush/fsync后发布；归档解包关闭文件并校验后发布目录，未逐文件fsync。
此前部分说明对恢复文件fsync描述过强，本版校正，不将未执行的操作计入结果或承诺掉电持久性。

"""
    for d in DATASETS:
        report=read(d+"-layout.json");prov=read(d+"-provenance.json");rows=report["results"]
        assert report["schema_version"]==12 and report["protocol"]["rounds"]==5
        assert report["implementation_checksums"]==checks
        assert report["files"]==prov["files"]==inventory(prov["source"])
        files={f["path"]:f for f in report["files"]}
        if d in NEW_SPECS:
            path,size,sha=NEW_SPECS[d];assert list(files.values())==[{"path":Path(path).name,"bytes":size,"sha256":sha}]
        elif d in OLD_SPECS:
            path,size,sha,*_=OLD_SPECS[d];assert list(files.values())==[{"path":Path(path).name,"bytes":size,"sha256":sha}]
        elif d=="ecg":assert {f["path"]:(f["bytes"],f["sha256"]) for f in files.values()}==NUMERIC_SPECS[d]["files"]
        expected=matrix(report["control_word_bytes"])
        assert [{k:v for k,v in r["configuration"].items() if k not in ("queries","seed")} for r in rows]==expected
        assert sorted(map(tuple,report["full_execution_order"]))==[(i,r) for i in range(20) for r in range(-1,5)]
        assert sorted(map(tuple,report["range_execution_order"]))==sorted((i,r,m) for i in range(20) for r in range(5) for m in ("open_reader","open_and_read"))
        counts={k:0 for k in totals};plans={}
        rec={"raw_bytes":report["raw_file_bytes"],"partition":prov["partition"],"conditions":{},"matched_comparisons":[],"acceptance":[],"minimum_archives":[]}
        result["datasets"][d]=rec
        layout=prov.get("layout") if isinstance(prov.get("layout"),dict) else None
        text+=f"## {d}\n\n{prov['partition']}；原始 {rec['raw_bytes']:,} B。\n\n"
        if layout:
            text+=f"BITPIX {layout['bitpix']}，FITS轴 {layout['fits_axes']}，头/图像/填充 {layout['header_bytes']:,}/{layout['image_bytes']:,}/{layout['padding_bytes']:,} B；NaN {layout['nan_words']:,}，正零 {layout['positive_zero_words']:,}/{layout['image_words']:,}（{100*layout['positive_zero_words']/layout['image_words']:.4f}%）。\n\n"
        tab=[]
        for r in rows:
            c=r["configuration"];assert r["bytewise_verified"] and r["deterministic_archive_bytes"]
            assert r["storage"]["stored_bytes"]==r["storage"]["payload_bytes"]+r["storage"]["metadata_bytes"]
            for phase in ("encode","decode"):
                ts=r[phase+"_trials"];assert [t["round"] for t in ts]==list(range(-1,5))
                assert all(t["bytewise_verified"] and t["blosc_loaded"] is False for t in ts)
                if phase=="encode":assert all(t["stats"]==r["storage"] for t in ts)
                else:
                    assert all(t["stats"]["raw_bytes"]==rec["raw_bytes"] for t in ts)
                    counts["formal_roundtrips"]+=5;counts["warmup_roundtrips"]+=1
            assert len(r["range_trials"])==10
            assert {(t["round"],t["mode"]) for t in r["range_trials"]}=={(n,m) for n in range(5) for m in ("open_reader","open_and_read")}
            for t in r["range_trials"]:
                assert t["bytewise_verified"]
                for group,g in t["groups"].items():
                    assert plans.setdefault((t["round"],group),g["request_sha256"])==g["request_sha256"]
                    assert g["verified_requests"]==len(g["requests"])
                    assert (len(g["latency_s"]["samples"]) if g["latency_s"] else 0)==g["verified_requests"]
                    counts["formal_range_reads"]+=g["verified_requests"];counts["warmup_range_reads"]+=g["verified_warmup_requests"]
            assert set(r["file_chunk_spans"])==set(files)
            for name,spans in r["file_chunk_spans"].items():
                cursor=0;boundaries={0}
                for i,(start,end,transform,codec) in enumerate(spans):
                    assert start==cursor and 0<end-start<=c["chunk_size"];cursor=end;boundaries.add(end)
                    if c["file_layout"]=="fixed":assert start==i*c["chunk_size"] and end==min((i+1)*c["chunk_size"],files[name]["bytes"])
                    if c["method"].startswith("typed") and transform!="none":
                        assert layout and layout["header_bytes"]<=start<end<=layout["header_bytes"]+layout["image_bytes"]
                        assert transform==f"byte-shuffle-{layout['word_bytes']}-v1"
                    if c["method"] in ("ordinary","segmented-none"):assert transform=="none"
                assert cursor==files[name]["bytes"]
                if layout and c["file_layout"]!="fixed":assert {layout["header_bytes"],layout["header_bytes"]+layout["image_bytes"]}<=boundaries
            expected_offset_bytes=(8*sum(len(spans)+1 for spans in r["file_chunk_spans"].values()) if c["file_layout"]!="fixed" else 0)
            assert r["layout_offset_bytes"]==expected_offset_bytes
            if d in ("ecg","noise") and c["method"].startswith("typed"):assert set(r["actual_transforms"]) and sum(v for k,v in r["actual_transforms"].items() if k!="none")==0
            if d=="noise":assert set(r["actual_codecs"])=={"raw"}
            charge=charges[c["method"]]
            rec["conditions"][label(r)]={"configuration":c,"storage":r["storage"],"allocated_once_bytes":charge,
                "layout_offset_bytes":r["layout_offset_bytes"],"actual_transforms":r["actual_transforms"],
                **{k:r[k] for k in ("encode_s","decode_s","encode_cpu_s","decode_cpu_s","encode_peak_rss_bytes","decode_peak_rss_bytes")},
                "resident_p95_s":p95(r,"open_reader"),"reopen_p95_s":p95(r,"open_and_read")}
            tab.append([label(r),r["storage"]["stored_bytes"],charge,r["layout_offset_bytes"],
                        f"{r['encode_s']['median']*1000:.3f}",f"{r['decode_s']['median']*1000:.3f}",
                        f"{p95(r,'open_reader')*1000:.3f}",f"{p95(r,'open_and_read')*1000:.3f}"])
        text+=table(["配置","归档 B","专用源一次 B","偏移数组 B","编码 ms","恢复 ms","常驻p95 ms","重开p95 ms"],tab)
        for codec in ("zlib","zstd"):
            for size in (65536,1048576):
                select=lambda method:next(r for r in rows if r["configuration"]["method"]==method and r["configuration"]["compression"]==codec and r["configuration"]["chunk_size"]==size)
                for base_name,candidate_name in (("ordinary","global-shuffle"),("ordinary","typed-fixed"),("ordinary","segmented-none"),
                        ("segmented-none","typed-segmented"),("typed-fixed","typed-segmented"),("global-shuffle","typed-segmented"),("ordinary","typed-segmented")):
                    b,cand=select(base_name),select(candidate_name)
                    old=b["storage"]["stored_bytes"]+charges[base_name];new=cand["storage"]["stored_bytes"]+charges[candidate_name]
                    rec["matched_comparisons"].append({"baseline":label(b),"candidate":label(cand),"archive_saving_pct":100*(1-cand["storage"]["stored_bytes"]/b["storage"]["stored_bytes"]),
                        "net_saving_pct_with_source_once":100*(1-new/old),"net_saved_bytes":old-new,
                        "paired":{m:paired(b,cand,m) for m in ("encode","decode","open_reader","open_and_read")}})
                comparisons=[x for x in rec["matched_comparisons"] if x["candidate"]==label(select("typed-segmented")) and x["baseline"] in (label(select("ordinary")),label(select("global-shuffle")))]
                assert len(comparisons)==2
                passed=all(x["net_saved_bytes"]>=0 and all(x["paired"][m]["speedup_median"]>=1 and x["paired"][m]["candidate_faster_rounds"]>=4 for m in ("decode","open_reader","open_and_read")) for x in comparisons)
                rec["acceptance"].append({"configuration":label(select("typed-segmented")),"passed":passed,"comparisons":comparisons})
        text+="\n### 同后端/块大小消融\n\n倍率为逐轮配对中位，大于1更快，括号为更快轮数；完整CPU/RSS/原始样本保留于JSON。\n\n"
        tab=[]
        for x in rec["matched_comparisons"]:
            def ratio(m):
                p=x["paired"][m];return f"{p['speedup_median']:.3f}× ({p['candidate_faster_rounds']}/5)"
            tab.append([x["baseline"],x["candidate"],f"{x['net_saving_pct_with_source_once']:.3f}%",*(ratio(m) for m in ("encode","decode","open_reader","open_and_read"))])
        text+=table(["基线","候选","计源净省","编码配对","恢复配对","常驻配对","重开配对"],tab)
        text+="\n### 预定联合验收\n\n须同时胜过同codec/块的ordinary与global-shuffle的预定门槛；编码独立披露，非综合支配判定。\n\n"
        text+=table(["分段类型配置","通过"],[[x["configuration"],x["passed"]] for x in rec["acceptance"]])
        ordinary=min((r for r in rows if r["configuration"]["method"]=="ordinary"),key=lambda r:r["storage"]["stored_bytes"])
        old=ordinary["storage"]["stored_bytes"]
        text+="\n### 每种方法事后最小归档\n\n限本矩阵的体积选参，不是预先固定的部署配置或速度最优；不替代上面的同配置验收。\n\n"
        for method in METHODS:
            r=min((r for r in rows if r["configuration"]["method"]==method),key=lambda r:r["storage"]["stored_bytes"])
            rec["minimum_archives"].append({"method":method,"configuration":label(r),"ordinary_bytes":old,
                "archive_bytes":r["storage"]["stored_bytes"],"allocated_once_bytes":charges[method],
                "net_saving_pct":100*(1-(r["storage"]["stored_bytes"]+charges[method])/old),
                "encode_median_s":r["encode_s"]["median"],"decode_median_s":r["decode_s"]["median"]})
        text+=table(["方法","最小配置","归档 B","加源后净省"],[[x["method"],x["configuration"],x["archive_bytes"],f"{x['net_saving_pct']:.3f}%"] for x in rec["minimum_archives"]])+"\n"
        rec["counts"]=counts;audit[d]={**counts,"conditions":len(rows),"input_sha_and_complete_cost_verified":True,"same_requests_and_exact_bytes_verified":True,"layout_spans_and_typed_boundaries_verified":True}
        for k in totals:totals[k]+=counts[k]
    aggregate=[]
    for method in METHODS:
        xs=[next(x for x in result["datasets"][d]["minimum_archives"] if x["method"]==method) for d in ("m13_64","rosat32")]
        old=sum(x["ordinary_bytes"] for x in xs);new=sum(x["archive_bytes"] for x in xs)
        aggregate.append({"method":method,"ordinary_bytes":old,"archive_bytes":new,"allocated_once_bytes":charges[method],"net_saving_pct":100*(1-(new+charges[method])/old)})
    result["validation_only_shared_resource"]=aggregate;result["totals"]=totals
    text+="## 两份新增验证输入合计，专用源共用一次\n\n这是独立归档加总，无CAS；每组事后选最小归档，不按速度选，M13大文件主导合计。\n\n"
    text+=table(["方法","合计归档 B","源一次 B","净省"],[[x["method"],x["archive_bytes"],x["allocated_once_bytes"],f"{x['net_saving_pct']:.3f}%"] for x in aggregate])
    text+=f"\n共{totals['formal_roundtrips']}次正式完整恢复、{totals['formal_range_reads']:,}次正式范围读取，另{totals['warmup_roundtrips']}次恢复预热、{totals['warmup_range_reads']:,}次查询预热，全部逐字节一致。\n\n"
    text+="新float64文件约11.6MB，ROSAT约22.66%正零，不能外推全部浮点科学数据。未识别ECG保守回退普通编码，会错过人工声明int16重排的收益；没有自动推断其通道/类型。五轮为描述统计，不给显著性或跨机器承诺。全部精确恢复不等于推理收益，无冷缓存/跨机器/跨日、数值Rust、CAS+布局或E3/E4结果。默认策略保持不变。\n"
    log_raw=test_log.read_bytes();log=log_raw.decode("utf-8-sig")
    ran=re.search(r"Ran (\d+) tests",log);status=re.search(r"^OK(?: \(skipped=(\d+)\))?\r?$",log,re.MULTILINE)
    assert ran and status and "FAILED (" not in log
    count,skip=int(ran[1]),int(status[1] or 0)
    validation={"datasets":audit,"frozen_python_source_identity_verified":True,"dedicated_source_cost_verified":True,
        "no_Blosc_loaded_in_any_formal_or_warmup_encode_decode_worker":True,"local_python_tests":{"run":count,"passed":count-skip,"skipped":skip,"failed":0,"log_sha256":hashlib.sha256(log_raw).hexdigest()},
        "acceptance_rule":"Predeclared docs/LAYOUT.md at 38473b2, all successes and failures retained",
        "persistence_scope":"Archive encode flush/fsync; unpack closes files and verifies before directory publish, without per-file fsync. Historical wording corrected; no crash-durability claim.",
        "cold_os_cache":None,"cross_machine":None,"inference_quality":None,"CAS_layout_integration":None}
    with (root/"SUMMARY.md").open("x",encoding="utf-8",newline="\n") as f:f.write(text)
    save(root/"derived-metrics.json",result);save(root/"validation.json",validation)
    return result


def plot(root,result):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(12,4.6),layout="constrained")
    for ax,d in zip(axes,("m13_64","rosat32")):
        xs=result["datasets"][d]["minimum_archives"]
        labels=[x["method"] for x in xs];values=[x["archive_bytes"]/1024 for x in xs]
        ax.bar(labels,values,color="#188567")
        ax.bar(labels,[x["allocated_once_bytes"]/1024 for x in xs],bottom=values,color="#d7a246",label="Whole dedicated sources once")
        ax.set_title(d);ax.set_ylabel("KiB, minimum complete archive per method")
        ax.tick_params(axis="x",rotation=25,labelsize=8);ax.grid(axis="y",alpha=.2);ax.set_axisbelow(True)
    axes[1].legend(fontsize=8);fig.suptitle("v0.12 new validation records - full original FITS bytes")
    out=root/"layout-costs.png"
    if out.exists():raise ValueError("Plot exists")
    fig.savefig(out,dpi=160);plt.close(fig)


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("root",type=Path);p.add_argument("--test-log",type=Path,required=True)
    p.add_argument("--plot",action="store_true");args=p.parse_args()
    result=analyze(args.root,args.test_log)
    if args.plot:plot(args.root,result)

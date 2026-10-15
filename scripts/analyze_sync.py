"""Audit sync/fault records and report end-to-end paired policy costs."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import statistics

from rkv1.controlled import implementation_checksums,inventory
from rkv1.benchmark import summary
from scripts.run_units import save
from scripts.summarize_units import table


def analyze(root,test_log):
    read=lambda n:json.loads((root/n).read_text("utf-8"))
    report=read("restore-sync.json");faults=read("fault-audit.json");checks=read("source-checksums.json")
    assert checks==report["implementation_checksums"]==implementation_checksums()
    resource=read("resource.json");raw=Path("rkv1/persistence.py").read_bytes()
    assert len(raw)==resource["persistence_source_bytes"] and hashlib.sha256(raw).hexdigest()==resource["persistence_source_sha256"]
    rows=[];totals={"formal_attempts":0,"formal_successes":0,"formal_failures":0,"warmup_attempts":0,"warmup_successes":0,"warmup_failures":0,"formal_completed_file_syncs":0,"formal_successful_publish_retries":0}
    text="""# v0.13.0 归档恢复文件同步、发布边界与历史账本更正

默认归档unpack变为files：完整原始文件SHA验证后flush→fsync→close，所有文件完成后发布目录；
空文件同步，任何同步错误失败，不静默降级。close为显式历史同步边界对照；两者同代码其他路径。
不改编码或归档格式，不声称压缩率改善。verify不写文件。目录/卷持久性、掉电、设备缓存承诺未验证。

四个案例同归档、同SHA、十轮正式，每策略一次预热，条件/轮次打乱、新进程分阶段测量。
计时含校验、同步、关闭、发布（包括Windows有界rename重试）和内部暂存清理，不含Python进程启动、
外部字节真值比较及删除输出。使用工作区scratch卷，温OS缓存、后台负载未隔离。
文件数控制是合成噪声切片130文件，不是真实科学目录。

初始试验在close路径复现WinError5目录rename，并暴露诊断编码问题；中止记录见attempt-history.json。
修订后对子进程强制UTF-8，只对Windows rename的5/32/33错误最多4次尝试，等待10/50/100ms，重查目标，
其他错误与永久失败传播；不重试同步或整次恢复、不修改ACL、不复制回退。所有job失败均保留。
以下主结果包括全部成功样本的发布重试等待；它是整个策略的观测成本，不是纯fsync内核延迟。

"""
    tab=[]
    rounds=report["protocol"]["rounds"];assert rounds==10
    expected=sorted((i,p,r) for i in range(4) for p in ("close","files") for r in range(-1,rounds))
    assert sorted(map(tuple,report["execution_order"]))==expected
    for case in report["cases"]:
        assert case["files"]==inventory(case["source"])
        assert case["storage"]["raw_bytes"]==sum(f["bytes"] for f in case["files"])
        trials=case["trials"];assert sorted((t["policy"],t["round"]) for t in trials)==sorted((p,r) for p in ("close","files") for r in range(-1,rounds))
        failures=[];retries=[]
        for t in trials:
            assert t["archive_sha256"]==case["storage"]["archive_sha256"]
            prefix="formal" if t["round"]>=0 else "warmup";totals[prefix+"_attempts"]+=1
            totals[prefix+("_successes" if t["success"] else "_failures")]+=1
            if t["success"]:
                assert t["bytewise_verified"] and t["stats"]["verified_files"]==len(case["files"])
                assert t["stats"]["raw_bytes"]==case["storage"]["raw_bytes"]
                assert t["stats"]["files_synced"]==(len(case["files"]) if t["policy"]=="files" else 0)
                assert 1<=t["stats"]["publish_attempts"]<=4
                if t["round"]>=0:
                    totals["formal_completed_file_syncs"]+=t["stats"]["files_synced"]
                    totals["formal_successful_publish_retries"]+=t["stats"]["publish_attempts"]-1
                if t["stats"]["publish_attempts"]>1:retries.append(t)
            else:
                assert t["error"] and (not t["target_present"] or t["target_bytewise_verified"])
                failures.append(t)
        selected={p:{t["round"]:t for t in trials if t["success"] and t["round"]>=0 and t["policy"]==p} for p in ("close","files")}
        pairs=sorted(set(selected["close"])&set(selected["files"]))
        def paired(indices):
            differences=[selected["files"][r]["wall_s"]-selected["close"][r]["wall_s"] for r in indices]
            ratios=[selected["files"][r]["wall_s"]/selected["close"][r]["wall_s"] for r in indices]
            return {"rounds":indices,"overhead_s":summary(differences),"files_div_close":summary(ratios),"files_slower_rounds":sum(x>1 for x in ratios)}
        main=paired(pairs);first=paired([r for r in pairs if selected["close"][r]["stats"]["publish_attempts"]==selected["files"][r]["stats"]["publish_attempts"]==1])
        row={"case":case["case"],"source_files":len(case["files"]),"raw_bytes":case["storage"]["raw_bytes"],"archive_bytes":case["storage"]["stored_bytes"],
             "archive_sha256":case["storage"]["archive_sha256"],"summaries":case["summaries"],"paired_all_successful_rounds":main,
             "secondary_both_first_publish_attempt":first,"retry_trials":retries,"failed_trials":failures}
        rows.append(row)
        def ms(policy):
            value=case["summaries"][policy]["wall_s"];return f"{value['median']*1000:.3f}" if value else "未完成"
        tab.append([case["case"],len(case["files"]),case["storage"]["stored_bytes"],ms("close"),ms("files"),
                    f"{main['overhead_s']['median']*1000:.3f}" if pairs else "未完成",
                    f"{main['files_div_close']['median']:.3f}×" if pairs else "未完成",len(pairs),len(retries),len(failures)])
    text+=table(["案例","文件数","同归档 B","close中位 ms","files中位 ms","配对额外 ms","files/close配对","有效配对轮数","含预热重试job","失败job"],tab)
    text+="\n差值/倍率是逐轮计算后取中位，与两个耗时中位之差/比不同。大于1的files/close表示更慢。原始wall/CPU/RSS保留于restore-sync.json。\n\n"
    text+="## 正式结果与故障边界\n\n"
    text+=f"正式 {totals['formal_attempts']} 次尝试，成功 {totals['formal_successes']}、失败 {totals['formal_failures']}；预热 {totals['warmup_attempts']} 次，成功 {totals['warmup_successes']}、失败 {totals['warmup_failures']}。成功输出全部逐字节一致，正式完成文件fsync请求 {totals['formal_completed_file_syncs']} 次；成功正式job的发布重试共 {totals['formal_successful_publish_retries']} 次，全部计入时序。\n\n"
    assert len(faults["records"])==198 and faults["all_expected_outcomes_verified"]
    from rkv1.experiments.restore_faults import CASES
    assert {(r["format"],r["repetition"],r["case"]) for r in faults["records"]}=={(v,n,c) for v in range(1,7) for n in range(3) for c in CASES}
    for r in faults["records"]:
        expected=r["case"] in ("normal-files","normal-close","kill-after-publish")
        assert r["target_present"]==expected
        if expected:assert r["bytewise_verified"]
        if r["case"].startswith("kill-"):assert r["private_staging_left"] and r["exit_code"]!=0
    text+="v1–v6 ×11情形×3轮，共198条故障审计均符合预定目标状态。写/flush/fsync/关闭/发布前失败不发布；发布前强杀目标不存在但会残留私有暂存；发布后强杀目标完整存在，客户端可能未收到成功。模拟异常与强杀不等于掉电、硬件故障全覆盖或自动恢复。\n\n"
    correction=read("v012-work-ledger-correction.json")
    assert correction["implementation_checksums"]==checks
    assert correction["historical_archives_reencoded_byte_identically"]==100 and correction["formal_requests_recomputed"]==96000
    changed=sum(bool(r["changed_groups"]) for d in correction["datasets"].values() for r in d["records"])
    groups=sum(len(r["changed_groups"]) for d in correction["datasets"].values() for r in d["records"])
    text+=f"## 历史工作量账本更正\n\nv0.12全部100个归档重编码的SHA及存储账本一致；96,000次原请求的解析工作量经前缀定位与独立线性扫描核对。{changed}个分段配置、{groups}个轮次/模式/类别账本需要更正。固定布局不变。没有新测读取延迟或覆盖旧结果；原成本/延迟及0/8联合验收计算不变。\n\n"
    text+="正式测量是当前同代码的同步策略对照，不跨版本计算加速。文件同步、目录发布、设备掉电保证分别看待；目录/卷同步、真实断电、跨机器/冷缓存/推理未测。Windows锁重试可能影响各轮时序，次级both-first-attempt子集仅诊断，不替代主结果。\n"
    raw_log=test_log.read_bytes();log=raw_log.decode("utf-8-sig")
    ran=re.search(r"Ran (\d+) tests",log);status=re.search(r"^OK(?: \(skipped=(\d+)\))?\r?$",log,re.MULTILINE)
    assert ran and status and "FAILED (" not in log
    count,skip=int(ran[1]),int(status[1] or 0)
    derived={"cases":rows,"totals":totals,"resource":resource,"fault_records":198,
             "historical_work_correction":{"archives":100,"formal_requests":96000,"changed_configurations":changed,"changed_groups":groups}}
    validation={"same_archive_every_policy_and_round":True,"all_successful_outputs_bytewise_verified":True,
        "all_failed_jobs_retained":True,"fsync_counters_verified":True,"frozen_source_verified":True,"fault_records_expected_states_verified":198,
        "historical_archives_byte_identity_verified":100,"historical_ledger_independent_overlap_verified":96000,
        "local_tests":{"run":count,"passed":count-skip,"skipped":skip,"failed":0,"log_sha256":hashlib.sha256(raw_log).hexdigest()},
        "power_failure":None,"directory_fsync":False,"automatic_orphan_recovery":False,"cold_os_cache":None,"cross_machine":None,"inference_quality":None}
    with (root/"SUMMARY.md").open("x",encoding="utf-8",newline="\n") as f:f.write(text)
    save(root/"derived-metrics.json",derived);save(root/"validation.json",validation)
    return derived


def plot(root,result):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(10,4.6),layout="constrained")
    xs=result["cases"];positions=list(range(len(xs)))
    for offset,policy,color in ((-.18,"close","#64748b"),(.18,"files","#188567")):
        values=[r["summaries"][policy]["wall_s"]["median"]*1000 for r in xs]
        bars=ax.bar([x+offset for x in positions],values,width=.34,label=policy,color=color)
        ax.bar_label(bars,fmt="%.2f",padding=3,fontsize=9)
    ax.set_xticks(positions,[r["case"] for r in xs]);ax.set_ylabel("ms, median of successful full restores")
    ax.set_title("v0.13 same archive: close vs verified-file flush/fsync\nWindows publish retry waits included; warm OS cache, one volume")
    ax.legend();ax.grid(axis="y",alpha=.2);ax.set_axisbelow(True);ax.set_ylim(0,ax.get_ylim()[1]*1.13)
    path=root/"restore-sync-costs.png"
    if path.exists():raise ValueError("Plot exists")
    fig.savefig(path,dpi=160);plt.close(fig)


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("root",type=Path);p.add_argument("--test-log",type=Path,required=True)
    p.add_argument("--plot",action="store_true");args=p.parse_args();result=analyze(args.root,args.test_log)
    if args.plot:plot(args.root,result)

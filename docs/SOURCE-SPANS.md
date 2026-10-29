# v0.92: exact sentence-token source binding

This is a mechanical representation study using owned fixtures only. It does not evaluate scientific retrieval, semantic entailment, compression, API answers or unknown-data generalization. The v0.89 scientific campaign remains closed and is never resumed.

## Frozen workload

One method, 18 fresh sequential child processes: rounds 1–3, each counts 3,17,65 in that order, each encoding `utf8_compact`, `escaped_pretty` in that order. Each child has 120 seconds, no retry; whole formal controller has 600 seconds. Record generation is the public `fixture` function: alternating explicit `abstract`/`sentences`, nested decoy, four string items including duplicated text, escaped/UTF-8 text and empty string. `escaped_pretty` means spaced JSON/escaped Unicode/CRLF, still one object per physical line. Selected sentence indices are exactly [0,2] for every record, without scores, gold, budget optimization or parameter search.

Exact totals: 510 original records, 1020 selected token recoveries, 108 negative controls, 18 checks that the old SID remains readable after HEAD advances. The smallest three-record compact case is used by necessary tests; 17/65 scale cases are not run before source/protocol/input SHA freeze and exact CI success.

## Identity contract

Caller explicitly supplies immutable snapshot SID, fixed path `corpus.jsonl`, full original file SHA, record offset/length/SHA and array field. A witness contains original string-token range (including quotes/escapes), original-token SHA, decoded UTF-8 SHA and original sentence index. Recovery receives the expected binding separately. It reads the complete original record through the normal Store range/CAS validation and re-parses the record, checking each index/range/digest. Duplicate identical strings are distinct positions. Neither source identity nor an externally supplied locator authenticates itself; a trusted caller must establish the expected binding.

An independently implemented byte-token recursive parser (no candidate scanner import) and complete physical JSONL record-boundary checker audit each original record and every selected token. The auditor opens a fresh pinned snapshot and verifies full original source SHA/bytes against the deterministic generator, then compares record boundaries/tokens and exact serialized packet SHA/costs. A valid nested subobject cannot stand in for a complete original record.

Six fixed case controls refuse: wrong external source, wrong external record, corrupted token digest, duplicate index, changed declared record count, changed witness SID. Later HEAD changes do not mutate the original SID. Actual CAS corruption is a necessary tiny-owned test, not another formal scale case. Source/record identities here are supplied by owned generation; they are not a cryptographic signature or external trust service.

## Predeclared gates and costs

H1 requires all 18 cases, 510 records, 1020 exact original token recoveries, 108 refusals, 18 old-SID checks, immutable formal artifacts, successful parent/child finalizers and independent record/token/packet/byte conservation. Missing/failing cases remain in these fixed denominators; no overwrite or retry.

H2 requires, in every primary 65-record case (six cells), total complete serialized packet bytes no greater than the complete original selected records. The packet explicitly serializes both witnesses and original tokens as hex. Witness cost, 2x hex expansion and full record reads are counted. This is a representation-cost feasibility gate, not a codec/net-compression or answer-quality gate. A negative result remains negative; no post hoc shared-index amortization, packet format change, record padding or alternate headline.

Report original source/record bytes, selected quoted token bytes, decoded UTF-8 bytes, serialized witness bytes, full packet bytes, original application-record bytes returned during the candidate phase, Store build, candidate construction+recovery phase, complete child/parent wall and CPU, peak RSS, complete independent audit, code/runtime/index/metadata/all case files and all inherited scientific/model/training/API artifacts. Candidate phase returns each original record twice (make and recover). Additional control, old-SID, complete audit, manifest/CAS/decode/OS traffic is not covered by that phase counter; uninstrumented total CAS/decode/physical I/O remains null. The candidate still parses full records and allocates O(N) character-to-byte offset maps; independent reference builds a token list and can have additional quadratic scanning overhead. No constant memory, speed or lower I/O claim is made.

A selected-token cap would differ from the old 4096-byte whole-record admission cap. This study introduces neither cap nor a new ranking/prompt. Complete source/runtime/library and packet costs cannot be hidden by a token-only total. All prior science/model/Store/snapshot/frame/restored/derived/failed/API costs remain inherited, not free.

## Reproduction and delivery

Run necessary tests and full regression, freeze all public runtime/program/test/protocol bytes and private worker/audit SHA, pass exact CI, then invoke only the unique guarded controller. Children have RKV_LLM environment variables removed, no model/network imports. Each case writes exclusive artifacts and full finally timing; every parent records startup-to-exit clocks. Scientific source/prompt/model/key files are never read. Independent audit and plotting have separate full timers. Actually inspect the chart before marking visual checks. Reports/source/README/release/local outside actual-wheel/native/sdist/CI/actual asset SHA/outside published installation/final proof redownload are required before delivery.

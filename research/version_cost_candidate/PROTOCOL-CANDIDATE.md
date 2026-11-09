# Candidate protocol for source and CI review

Status: preparation only. No real data or performance observations are included here.

The usage task is exact known-path recovery from continuously updated current/history files.
Compare per-version/per-file Zstd, cumulative solid tar+Zstd, and the unchanged default RKV
original-byte Store with its persistent logical-version map. No FTS, ranking, semantic-answer,
NLI or infinite-context claim belongs to this task.

The private preselected catalog has12 chronological versions and2 original paths:
README.md and docs/ROADMAP.md. Its identities and the input/plan hashes are frozen externally;
CI receives synthetic fixtures only. No change to input selection, compression parameters,
role order or thresholds is permitted after real results appear.

Use all6 permutations of3 roles, each with a new independent library, giving18 libraries.
Each library has12 update processes, each followed by a separate process validating the
entire committed history, then12 cold-process reads. Read selectors are explicitv000,
explicitv005 and currentv011; each has2 known paths, one missing path and one full restore.
There are648 data/validation processes,1404 validation restores and2808 history file checks;
cold reads add108 known reads,54 missing reads and54 restores. Repeat orders describe
machine variability, not independent scientific families; do not report family significance.

API timers surround the unmodified archive calls, including ordinary internal verification
and lazy imports. Setup/source checks, external comparison/copy/fsync, independent validation,
quota preflight and controller/audit costs are separate. Whole-process time/RSS is recorded
without subtraction; cold process does not mean cold OS cache. Before/after inventories
warm files and prove endpoint equality only, not absence of transient writes or hostile actors.

Keep application history/safety logs, incremental source deployment and all research overhead
in separate ledgers, plus their explicit union. Existing Python is the source-mode premise;
whole Python/system closure and published-wheel footprint remain unknown. Native quota CLI
is research tooling. Logical bytes are not physical IO, payload is not RSS, and overlapping
parent/child intervals are not additive. Preserve failed and historical costs; unknown is not0.

Promotion requires at least10% AND65536 bytes saved against BOTH simple controls, including
incremental source deployment. Wall fails only if BOTH greater than1.5x AND20ms extra;
RSS fails only if BOTH greater than1.25x AND16MiB extra. Apply wall guards to API and raw
whole-process time separately. Use the exact median of6 observations and fixed maxima,
retain every raw value; CPU is descriptive. Missing evidence cannot pass or imply inefficacy.

One serial global budget owns all libraries and requests. Per-task bounds:30s,512MiB RSS;
library64MiB, output root1GiB. Every process requires a fresh actual official preflight,
at most10s with2s shared cleanup reserve. The original total wall1800s is not proven feasible;
3600s is a review-only alternative, not accepted permission or a completion guarantee.
Final admission must bind the selected budget and exact immutable plan/source/input hashes.

Each quota observation binds its own task ID and plan digest inside the preflight specification.
The coordinator verifies that specification and reads the observation from that exact task directory.
An observation from a different row cannot grant permission.

The independent result reader takes externally retained plan and terminal digests. It verifies
the journal chain and all 648 task receipts, including actual exits, quota observations, library
endpoints and 3024 saved original files. A stopped run keeps its full denominator and receives
no score. For a complete run, pair retained library bytes by order and report all six pairs for
each baseline, with and without deployment. All six deployment-inclusive pairs must meet
the space threshold for that comparison. For timing and RSS compare each fixed update or cold
read across its six observations. For total update wall, sum the twelve disjoint update intervals
per library separately for API and whole-process wall. History-check resources remain in the
ledger and separate from the scored update and read intervals.

Unknown/denied/100% quota, unauthorized window, bad source/identity/output/exit witness,
budget exhaustion or unavailable measurement stops the full run. Do not retry, fill missing
slots, recycle roots, roll back or lower denominators. Missing receipts alone cannot prove
globally unattempted work. Preserve exact partial state and unknown costs.

Real execution remains blocked until explicit human/window authorization, accepted budget,
final code/protocol/input freeze, and successful CI for that exact candidate source are bound.
This source review and its owned fixture checks do not authorize real12 execution or release.

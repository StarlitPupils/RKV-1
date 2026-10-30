# v0.93 source distribution scope and reproducibility

The source distribution now includes all runtime/Python/HTML, scripts, tests and owned fixtures, docs/protocols/manifests, Rust source, license/build configuration, and **current-version experiment outputs only**. Historical results remain unchanged in Git and their original tagged releases. See RESULTS-INDEX.md for immutable original paths. Older analysis scripts needing historical results require the corresponding Git/tag checkout (and private scientific inputs where applicable); the small sdist is not an offline archive of all historical runs. Wheel defaults and scientific algorithms are unchanged.

This changes distribution contents. A smaller archive is **not lossless scientific compression**, model gain, lower inference cost or a network speed measurement. No historical report, result, tag, asset or negative conclusion is deleted or rewritten.

## Frozen experiment

After exact source/protocol/input SHA freeze and successful exact CI, build once with `python -m build --no-isolation`, preserving logs and artifacts in an exclusive private directory. One fresh subprocess, 600 seconds, zero retry. The formal distribution includes only the frozen v0.93 seed report; later publication builds additionally include the final report/raw/chart and have distinct size/SHA. Do not equate the formal/local archive with the CI-published asset; both require independent audits.

H1: all expected source/current-output members have exact original SHA, no missing or duplicate or unsafe/link/private/historical-results members, runtime recursive source/HTML retained, historical per-version Git trees identical to their v0.92 completion-main identities. Independent complete-member enumeration and streaming SHA audit must cross-check the candidate auditor. Keep synthetic negative-member controls in tests.

H2: formal compressed sdist size at most 10% of the actual prior v0.92 source asset size 164035251 bytes. This is a scoped-delivery feasibility gate under explicitly different contents, not a codec comparison. No content/threshold tuning after the formal build. Also report complete uncompressed member totals, runtime/scripts/tests/docs/Rust counts, original retained history volume, wheel size, full parent/build/audit CPU/wall/RSS, code/library and old scientific/Store/model/API/failed-transfer costs. Transfer wall/reliability are not measured here.

No scientific corpus/gold/model/old API response or model/provider request is used. The old v0.89 failed campaign stays closed. Exact current package-member and source-byte audit must be repeated on the final local package and actual CI-published sdist, followed by physical outside installation of actual wheel/current native and all existing owned sdist checks. Full publication assets/SHA/source/installation/proof redownload remain required before delivery. Build and final package/install/proof costs are separate; do not backfill clocks into older science.

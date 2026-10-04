# Real review iterations

The initial complete implementation is baseline `fb288f038a5be58d69dd79bd689d7a4f6c68ab54`, not a correction cycle. Evidence paths below are relative to the separate `implementation/noticeforge` directory. Full successor hashes and replay commands are recorded by HANDOFF once verification finishes.

## 1: Valid folded wheel metadata wrongly refused

Original `probe_folded_metadata.py` constructs a valid ordinary wheel whose License-Expression uses a legal email continuation line. It recomputes and independently checks every RECORD hash/size; native pip installs it successfully. Baseline SDK raised InputError and registered CLI exited 2, despite an approved `MIT OR Apache-2.0` expression and choice MIT. `folded-before-record-valid` exits 1 with complete inputs/raw SDK/CLI/pip evidence. The first draft probe had a stale RECORD entry after rewriting METADATA; its original failure is retained as `folded-before`, but the corrected valid-wheel rerun supplies this product finding.

The actual field parser now unfolds legal continuation lines through Python's email header registry before checking the field contract, while preserving the original METADATA bytes. The native consumer handles legal folding and a targeted supported-input test checks publication. The unchanged corrected probe is replayed against the ordinary successor wheel. This is a product compatibility correction, distinct from the preliminary probe RECORD repair.

Ordinary after `eae948bd89bef7c4e4323ed333828efa5956b4cf`: `folded-after` exits 0, native pip 0, SDK PUBLISHED, registered CLI 0. Nine installed tests pass. The native consumer uses Python's standard email implementation independently of product code; it remains a collection consumer, not a legal opinion.

## 2: ZIP raw NUL path loses original material attribution

`probe_raw_zip_name.py` preserves an archive entry's raw original filename containing NUL, updates all approved artifact hashes, and records both ZipInfo.orig_filename and filename. Python zipfile truncates the latter. Baseline and ordinary round1 `eae948bd89bef7c4e4323ed333828efa5956b4cf` incorrectly published, reporting a source path that was not the original path. `raw-name-before` and `raw-name-before-round1` both exit 1, SDK/CLI PUBLISHED/0 with full artifacts and receipts preserved.

Before any material read/staging, the product now checks that the original decoded ZIP name exactly equals the name exposed to lookups, rejecting normalization/truncation. It still validates portable relative path syntax. A targeted raw-archive test checks no published directory, and the unchanged original probe supplies ordinary-wheel after evidence. This is an incorrect acceptance and attribution defect, not a ZIP parser novelty claim.

Ordinary after `43e0ac0687e9326f16b4f747b7d25c4365db7c93`: `raw-name-after` exits 0, SDK refuses, CLI exits 2, both destinations absent. Ten installed tests pass.

## 3: Case-alias parent directories corrupt the published inventory

`probe_directory_alias.py` uses distinct leaf names Legal/LICENSE and legal/AUTHORS, with no explicit ZIP directory entries. Baseline and ordinary round2 `43e0ac0687e9326f16b4f747b7d25c4365db7c93` published with CLI 0, but Windows merged the two parent directories: actual `Legal/AUTHORS` disagreed with manifest `legal/AUTHORS`. `directory-alias-before` and `directory-alias-before-round2` exit 1 with original bytes, full output and native inventory mismatch retained. Both leaves alone had passed the prior full-path collision check.

The product now validates every explicit and implicit path ancestor under NFC/case folding and enforces a consistent original spelling and directory/file kind. It refuses case/Unicode ancestor aliases and file/directory collisions before material reads or staging. Targeted tests cover different leaf names under case and NFC-equivalent parents. The unchanged original probe supplies ordinary-wheel after evidence.

Ordinary after `4266c8a07bfe1a588fe47543ea3352b5b309d684`: `directory-alias-after` exits 0, SDK refuses, CLI 2, no destination. Eleven installed tests pass.

## 4: Corrupt compression escapes the controlled refusal contract

After the three corrections, a further actual archive test found that a reserved DEFLATE block type raised zlib.error outside the InputError mapping. `probe_deflate_error.py` updates actual wheel/BOM/approval hashes to the corrupted bytes, preserving the malformed original artifact. Ordinary before `4266c8a07bfe1a588fe47543ea3352b5b309d684` produced SDK zlib.error, registered CLI traceback/exit 1; `deflate-before` exits 1. Nothing was published, so this is an interface refusal defect rather than a false successful publication.

Known decompressor/EOF errors are now mapped to the same controlled InputError/CLI REFUSED exit 2 as BadZipFile, with no publication. A targeted real compressed-input test and the unchanged original probe verify the correction. This fourth real correction is additional evidence; the first three already concern distinct supported workflow defects. No failure was intentionally inserted to create a cycle.

Ordinary after `b41a1520f2f1f79d3711156b60068be118f70a6c`: `deflate-after` exits 0, SDK InputError, registered CLI REFUSED/2, no traceback/publication. Twelve installed tests pass. The first three unchanged probes also pass against this ordinary candidate (`folded-final`, `raw-name-final`, `directory-alias-final`).

Final runtime audit: 130 original-input boundary/selection records include all nine resource budget minus-one/exact/plus-one cases, booleans/huge integers, duplicate JSON/BOM refs, dangling/missing adjacency and approvals, invalid UTF-8/NaN, LicenseRef/WITH/repeated-atom generated branch cases, and three fully consumed 1 MiB material boundary files (3,145,728 material bytes). Three actual product process IDs were terminated after a durable first file, just before rename and just after rename; only the last had a published directory, fully checked by the native consumer. Actual Windows exclusive-read input failure maps to SDK InputError/CLI 2 without output. Hardlink alias and nested input directory output refuse without changing source bytes. Windows symlink creation lacks privilege locally (WinError 1314); that skip is preserved, and a corresponding source test runs where supported. These verification/test additions are not extra correction cycles.

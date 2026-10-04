# Real review iterations

The initial complete implementation is baseline `fb288f038a5be58d69dd79bd689d7a4f6c68ab54`, not a correction cycle. Evidence paths below are relative to the separate `implementation/noticeforge` directory. Full successor hashes and replay commands are recorded by HANDOFF once verification finishes.

## 1: Valid folded wheel metadata wrongly refused

Original `probe_folded_metadata.py` constructs a valid ordinary wheel whose License-Expression uses a legal email continuation line. It recomputes and independently checks every RECORD hash/size; native pip installs it successfully. Baseline SDK raised InputError and registered CLI exited 2, despite an approved `MIT OR Apache-2.0` expression and choice MIT. `folded-before-record-valid` exits 1 with complete inputs/raw SDK/CLI/pip evidence. The first draft probe had a stale RECORD entry after rewriting METADATA; its original failure is retained as `folded-before`, but the corrected valid-wheel rerun supplies this product finding.

The actual field parser now unfolds legal continuation lines through Python's email header registry before checking the field contract, while preserving the original METADATA bytes. The native consumer handles legal folding and a targeted supported-input test checks publication. The unchanged corrected probe is replayed against the ordinary successor wheel. This is a product compatibility correction, distinct from the preliminary probe RECORD repair.

Ordinary after `eae948bd89bef7c4e4323ed333828efa5956b4cf`: `folded-after` exits 0, native pip 0, SDK PUBLISHED, registered CLI 0. Nine installed tests pass. The native consumer uses Python's standard email implementation independently of product code; it remains a collection consumer, not a legal opinion.

## 2: ZIP raw NUL path loses original material attribution

`probe_raw_zip_name.py` preserves an archive entry's raw original filename containing NUL, updates all approved artifact hashes, and records both ZipInfo.orig_filename and filename. Python zipfile truncates the latter. Baseline and ordinary round1 `eae948bd89bef7c4e4323ed333828efa5956b4cf` incorrectly published, reporting a source path that was not the original path. `raw-name-before` and `raw-name-before-round1` both exit 1, SDK/CLI PUBLISHED/0 with full artifacts and receipts preserved.

Before any material read/staging, the product now checks that the original decoded ZIP name exactly equals the name exposed to lookups, rejecting normalization/truncation. It still validates portable relative path syntax. A targeted raw-archive test checks no published directory, and the unchanged original probe supplies ordinary-wheel after evidence. This is an incorrect acceptance and attribution defect, not a ZIP parser novelty claim.

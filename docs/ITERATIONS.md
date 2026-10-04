# Real review iterations

The initial complete implementation is baseline `fb288f038a5be58d69dd79bd689d7a4f6c68ab54`, not a correction cycle. Evidence paths below are relative to the separate `implementation/noticeforge` directory. Full successor hashes and replay commands are recorded by HANDOFF once verification finishes.

## 1: Valid folded wheel metadata wrongly refused

Original `probe_folded_metadata.py` constructs a valid ordinary wheel whose License-Expression uses a legal email continuation line. It recomputes and independently checks every RECORD hash/size; native pip installs it successfully. Baseline SDK raised InputError and registered CLI exited 2, despite an approved `MIT OR Apache-2.0` expression and choice MIT. `folded-before-record-valid` exits 1 with complete inputs/raw SDK/CLI/pip evidence. The first draft probe had a stale RECORD entry after rewriting METADATA; its original failure is retained as `folded-before`, but the corrected valid-wheel rerun supplies this product finding.

The actual field parser now unfolds legal continuation lines through Python's email header registry before checking the field contract, while preserving the original METADATA bytes. The native consumer handles legal folding and a targeted supported-input test checks publication. The unchanged corrected probe is replayed against the ordinary successor wheel. This is a product compatibility correction, distinct from the preliminary probe RECORD repair.

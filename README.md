# NoticeForge

Publish the actual license material bytes for an explicitly selected CycloneDX dependency closure. A release engineer supplies human approvals, wheel artifacts and hashes; NoticeForge verifies agreement and creates a new NOTICE directory with lossless component, artifact, license and path attribution. A separate consumer checks every output file against the original wheels.

Python 3.11+; MIT. Customers, revenue and production adoption are unknown. The included invoice integration is an author-created local laboratory application.

```console
python -m pip install .
noticeforge forge --bom bom.json --approvals approvals.json --wheel-dir wheels --output distribution-notices
python examples/consumer.py bom.json approvals.json wheels distribution-notices
```

The SDK exposes `forge(bom, approvals, wheel_dir, output, limits=Limits(...))`. It returns `PUBLISHED` only after collecting, hashing, writing and rereading every output byte. Invalid or unverifiable input raises `InputError`; the CLI emits `REFUSED` on stderr and exits 2. The destination must be new. Input files are read, never edited. A crash can leave a sibling `.noticeforge-stage-*` directory; review and remove orphan staging manually. No automatic deployment or overwrite occurs.

Run the complete local integration:

```console
python -m pip install "setuptools>=77" wheel
python examples/pilot.py pilot-output --cli noticeforge
python -m unittest discover -s tests -v
```

The pilot builds application wheels with `--no-build-isolation`, so it requires these explicit development build tools in the Python environment running the example. They are not NoticeForge runtime dependencies. Invoke the example as documented with ordinary Python so its adjacent independent `consumer.py` can be imported; the product wheel itself is separately tested with `python -I` and the actual registered CLI.

The pilot builds five real wheels with setuptools, installs four into a separate environment, invokes their registered invoice CLI with actual CSV, checks the invoice using independent integer arithmetic, and compares the same notice materials with an independent correct manual collection baseline. It retains every output and repeated timing. CLI startup, validation, hashing and fsync can cost more than a simple copier for small inputs; timings do not establish human time savings.

Supported inputs are a bounded **CycloneDX JSON 1.6 subset**, flat application/library components, one declared SPDX expression per component, an explicit dependency row for every component, and Python wheels with metadata 2.4, 2.5 or 2.6. Each component carries one SHA-256 for the particular wheel, which must agree with approval and actual bytes. No dependency resolution from `Requires-Dist` is inferred: the supplied complete graph and explicit roots define the shipped closure. Unreachable development components are recorded as excluded. A graph containing a reachable development component includes it.

Every wheel `License-File` is copied, including additional attribution and materials from unselected alternatives. Responsible humans approve the source expression, chosen branch and file-to-license mapping. These decisions are inputs; their identity is not authenticated. The tool proves collection consistency within the supplied contract, not whether a notice is legally sufficient, whether the author has licensing rights, or whether the SBOM includes all software actually shipped. See [DESIGN](docs/DESIGN.md) for bounds and assumptions, [PILOT](docs/PILOT.md) for the comparator, and [ITERATIONS](docs/ITERATIONS.md) for actual review history.

This is not a new license expression or policy checker. [SPDX expressions](https://spdx.github.io/spdx-spec/v2.3/SPDX-license-expressions/), [CycloneDX 1.6](https://github.com/CycloneDX/specification/blob/1.6/schema/bom-1.6.schema.json), [Dependency-Track policy compliance](https://docs.dependencytrack.org/usage/policy-compliance/), [PyPA metadata](https://packaging.python.org/en/latest/specifications/core-metadata/), [PEP 639](https://peps.python.org/pep-0639/) and [packaging's license validator](https://packaging.pypa.io/en/stable/licenses.html) supply mature standards and primitives. The implemented workflow joins the selected closure, approved artifact identity, actual wheel material bytes and independently consumed publication. Sources checked 2026-10-05; comparison does not assert that other products cannot implement this workflow.

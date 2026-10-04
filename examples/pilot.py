"""Real local invoice application wheels, installed CLI, complete material consumer.

Artifacts and approvals are authored LAB fixtures; no customer/production claims.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import venv
import zipfile
from email.parser import Parser
from pathlib import Path
from consumer import consume


def hashed(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def command(args, cwd, log):
    started = time.perf_counter_ns()
    completed = subprocess.run([str(item) for item in args], cwd=cwd, capture_output=True, timeout=120)
    log.parent.mkdir(parents=True, exist_ok=True)
    log.with_suffix(".stdout").write_bytes(completed.stdout)
    log.with_suffix(".stderr").write_bytes(completed.stderr)
    log.with_suffix(".json").write_bytes(encoded({"args": [str(item) for item in args], "cwd": str(cwd),
         "returncode": completed.returncode, "elapsed_ns": time.perf_counter_ns() - started}))
    if completed.returncode:
        raise RuntimeError(f"command failed: {args}; see {log}.stderr")
    return completed.stdout


def manual_collect(bom_path, policy_path, wheels, out):
    """Correct approved report + material collection baseline, separate algorithm.

    Human approval is already provided. Checks all artifact and material bytes;
    independently materializes the same consumer contract, no product imports.
    """
    bom_raw, policy_raw = bom_path.read_bytes(), policy_path.read_bytes()
    bom, policy = json.loads(bom_raw), json.loads(policy_raw)
    by_ref = {item["bom-ref"]: item for item in bom["components"] + [bom["metadata"]["component"]]}
    adjacency = {item["ref"]: item["dependsOn"] for item in bom["dependencies"]}
    reached = set(policy["roots"])
    for _ in by_ref:
        reached |= {target for ref in tuple(reached) for target in adjacency[ref]}
    assert reached == set(policy["components"])
    payloads = {"inputs/bom.json": bom_raw, "inputs/approvals.json": policy_raw}
    records = []
    notice = ["NOTICE material collection", "Human approvals: " + policy["approved_by"],
              "Collection consistency only; no legal compliance determination.", ""]
    for ref in sorted(reached):
        approval, item = policy["components"][ref], by_ref[ref]
        raw = (wheels / approval["artifact"]).read_bytes()
        assert hashed(raw) == approval["sha256"]
        assert hashed(raw) in [h["content"] for h in item["hashes"] if h["alg"] == "SHA-256"]
        prefix = "components/" + hashed(ref.encode())
        with zipfile.ZipFile(wheels / approval["artifact"]) as wheel:
            metadata_path, = [name for name in wheel.namelist() if name.endswith(".dist-info/METADATA")]
            metadata = wheel.read(metadata_path)
            headers = Parser().parsestr(metadata.decode())
            assert headers["License-Expression"] == item["licenses"][0]["expression"] == approval["expression"]
            assert set(headers.get_all("License-File")) == set(approval["materials"])
            payloads[prefix + "/METADATA"] = metadata
            entries = []
            for path in headers.get_all("License-File"):
                source = metadata_path.rsplit("/", 1)[0] + "/licenses/" + path
                data = wheel.read(source)
                assert hashed(data) == approval["materials"][path]["sha256"]
                target = prefix + "/licenses/" + path
                payloads[target] = data
                entries.append({"license_file": path, "source_path": source, "output_path": target,
                     "sha256": hashed(data), "bytes": len(data), "licenses": approval["materials"][path]["licenses"]})
        record = {"bom_ref": ref, "name": item["name"], "version": item["version"],
                 "expression": approval["expression"], "artifact_sha256": approval["sha256"],
                 "artifact": approval["artifact"], "choice": approval["choice"], "metadata_version": headers["Metadata-Version"],
                 "metadata_path": metadata_path, "metadata_output": prefix + "/METADATA", "metadata_sha256": hashed(metadata), "materials": entries}
        records.append(record)
        notice += [ref, f"  {record['name']} {record['version']}", "  Declared: " + record["expression"], "  Approved atoms: " + ", ".join(record["choice"])]
        notice += ["  Material: " + entry["output_path"] for entry in entries]
    payloads["NOTICE.txt"] = ("\n".join(notice) + "\n").encode()
    manifest = {"format": "noticeforge-bundle/v1", "roots": policy["roots"], "excluded": sorted(set(by_ref) - reached),
         "dependencies": adjacency, "components": records, "inputs": {"bom_sha256": hashed(bom_raw), "approvals_sha256": hashed(policy_raw)},
         "files": [{"path": path, "bytes": len(data), "sha256": hashed(data)} for path, data in sorted(payloads.items())]}
    payloads["manifest.json"] = encoded(manifest)
    out.mkdir()
    for path, data in payloads.items():
        destination = out / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
    return len(payloads), sum(map(len, payloads.values()))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--cli", default="noticeforge")
    args = parser.parse_args()
    cli_path = shutil.which(args.cli) or str(Path(args.cli).resolve())
    root = Path(args.output).resolve()
    root.mkdir(parents=True, exist_ok=False)
    preparation = time.perf_counter_ns()
    wheels = root / "wheels"
    wheels.mkdir()
    names = ["invoice_app", "invoice_calc", "invoice_tax", "invoice_money", "invoice_dev"]
    dependencies = {"invoice_app": ["invoice_calc", "invoice_tax"], "invoice_calc": ["invoice_money"],
         "invoice_tax": ["invoice_money"], "invoice_money": ["invoice_calc"], "invoice_dev": []}
    sources = {
        "invoice_app": "import csv, sys\nfrom invoice_calc import subtotal\nfrom invoice_tax import taxed\ndef main():\n    total = sum(taxed(subtotal(int(r['units']), int(r['price']))) for r in csv.DictReader(sys.stdin))\n    print(total)\n",
        "invoice_calc": "from invoice_money import checked\ndef subtotal(units, price):\n    return checked(units * price)\n",
        "invoice_tax": "from invoice_money import checked\ndef taxed(value):\n    return checked(value + value // 10)\n",
        "invoice_money": "def checked(value):\n    if value < 0: raise ValueError('negative invoice')\n    return value\n",
        "invoice_dev": "def development_only(): return 'not shipped'\n"}
    components, approvals = [], {}
    mit = (Path(__file__).resolve().parents[1] / "LICENSE").read_bytes()
    for name in names:
        project = root / "sources" / name
        (project / "legal/a").mkdir(parents=True)
        (project / "legal/b").mkdir()
        (project / "legal/a/LICENSE").write_bytes(mit)
        (project / "legal/b/LICENSE").write_bytes(("Additional author attribution: " + name + " 版权\r\n").encode())
        (project / (name + ".py")).write_text(sources[name], encoding="utf-8")
        config = '[build-system]\nrequires=["setuptools>=77"]\nbuild-backend="setuptools.build_meta"\n[project]\n'
        config += f'name="{name}"\nversion="1.0"\nlicense="MIT OR LicenseRef-OrderLab"\nlicense-files=["legal/a/LICENSE", "legal/b/LICENSE"]\n'
        if name == "invoice_app":
            config += '[project.scripts]\nlab-invoice="invoice_app:main"\n'
        config += f'[tool.setuptools]\npy-modules=["{name}"]\n'
        (project / "pyproject.toml").write_text(config, encoding="utf-8")
        command([sys.executable, "-m", "pip", "wheel", "--no-build-isolation", "--no-deps", "--wheel-dir", wheels, project], root, root / "logs" / ("build-" + name))
        artifact, = wheels.glob(name + "-*.whl")
        checksum = hashed(artifact.read_bytes())
        components.append({"type": "application" if name == names[0] else "library", "bom-ref": name, "name": name, "version": "1.0",
            "licenses": [{"expression": "MIT OR LicenseRef-OrderLab"}], "hashes": [{"alg": "SHA-256", "content": checksum}]})
        with zipfile.ZipFile(artifact) as archive:
            prefix, = [p.rsplit("/", 1)[0] for p in archive.namelist() if p.endswith(".dist-info/METADATA")]
            materials = {path: {"sha256": hashed(archive.read(prefix + "/licenses/" + path)),
                         "licenses": ["MIT" if path.endswith("a/LICENSE") else "LicenseRef-OrderLab"]}
                         for path in ("legal/a/LICENSE", "legal/b/LICENSE")}
        approvals[name] = {"artifact": artifact.name, "sha256": checksum, "expression": "MIT OR LicenseRef-OrderLab", "choice": ["MIT"], "materials": materials}
    bom = {"bomFormat": "CycloneDX", "specVersion": "1.6", "version": 1, "metadata": {"component": components[0]}, "components": components[1:],
           "dependencies": [{"ref": name, "dependsOn": dependencies[name]} for name in names]}
    (root / "bom.json").write_bytes(encoded(bom))
    policy = {"format": "noticeforge-approvals/v1", "approved_by": "LAB AUTHOR; not legal advice", "roots": ["invoice_app"],
              "components": {name: approvals[name] for name in names[:-1]}}
    (root / "approvals.json").write_bytes(encoded(policy))
    prep_ns = time.perf_counter_ns() - preparation
    env = root / "invoice-env"
    venv.EnvBuilder(with_pip=True).create(env)
    python = env / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    command([python, "-m", "pip", "install", "--no-index", *[wheels / approvals[name]["artifact"] for name in names[:-1]]], root, root / "logs/install-invoice")
    invoice_cli = env / ("Scripts/lab-invoice.exe" if os.name == "nt" else "bin/lab-invoice")
    input_bytes = b"units,price\n2,100\n3,250\n1,99\n"
    result = subprocess.run([invoice_cli], input=input_bytes, capture_output=True, timeout=30)
    (root / "invoice.csv").write_bytes(input_bytes)
    (root / "invoice.stdout").write_bytes(result.stdout)
    (root / "invoice.stderr").write_bytes(result.stderr)
    expected_total = sum((u*p)+(u*p)//10 for u,p in [(2,100),(3,250),(1,99)])
    assert result.returncode == 0 and result.stdout in (f"{expected_total}\n".encode(), f"{expected_total}\r\n".encode())
    outcomes = []
    for case, refs in (("diamond-cycle", ["invoice_app"]), ("small-no-benefit", ["invoice_money"])):
        case_dir = root / case
        case_dir.mkdir()
        reached = set(refs)
        for _ in names:
            reached |= {target for ref in tuple(reached) for target in dependencies[ref]}
        # Use a genuine one-component closure for the small case.
        if case == "small-no-benefit":
            case_bom = {**bom, "dependencies": [{"ref": n, "dependsOn": []} for n in names]}
            reached = set(refs)
        else:
            case_bom = bom
        case_policy = {**policy, "roots": refs, "components": {ref: approvals[ref] for ref in reached}}
        (case_dir / "bom.json").write_bytes(encoded(case_bom))
        (case_dir / "approvals.json").write_bytes(encoded(case_policy))
        for repeat in range(3):
            for method in (["manual", "forge"] if repeat % 2 == 0 else ["forge", "manual"]):
                out = case_dir / f"{method}-{repeat}"
                started = time.perf_counter_ns()
                if method == "manual":
                    manual_collect(case_dir / "bom.json", case_dir / "approvals.json", wheels, out)
                else:
                    command([cli_path, "forge", "--bom", case_dir / "bom.json", "--approvals", case_dir / "approvals.json", "--wheel-dir", wheels, "--output", out], root,
                            root / "logs" / f"{case}-{repeat}-{method}")
                elapsed = time.perf_counter_ns() - started
                consumer = consume(case_dir / "bom.json", case_dir / "approvals.json", wheels, out)
                outcomes.append({"case": case, "repeat": repeat, "method": method, "elapsed_ns": elapsed, "consumer": consumer})
    summary = {"scope": "author-created local lab, no customer/production claims", "builds": 5,
          "preparation_ns": prep_ns, "approval_decisions": 4, "material_hash_decisions": 8,
          "installed_invoice_exit": result.returncode, "invoice_expected": expected_total, "invoice_stdout_sha256": hashed(result.stdout),
          "baseline_note": "Correct preapproved report + independent material copier; in-process manual vs registered forge CLI includes CLI startup cost. No human-time saving inferred.",
          "runs": outcomes}
    (root / "summary.json").write_bytes(encoded(summary))
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()

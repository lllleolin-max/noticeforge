"""Separate native consumer. No noticeforge imports or expression parser reuse.

Requires the human's original inputs and independently checks graph reachability,
all License-File bytes and complete output inventory. Does not assess legal rights.
"""
import hashlib
import json
import sys
import zipfile
from email.parser import Parser
from email.policy import default
from pathlib import Path


def consume(bom_path, policy_path, wheels, output):
    bom_bytes, policy_bytes = Path(bom_path).read_bytes(), Path(policy_path).read_bytes()
    bom, policy = json.loads(bom_bytes), json.loads(policy_bytes)
    out = Path(output)
    manifest_bytes = (out / "manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    original = bom.get("components", []) + [bom["metadata"]["component"]]
    components = {item["bom-ref"]: item for item in original}
    assert len(components) == len(original)
    adjacency = {item["ref"]: item["dependsOn"] for item in bom["dependencies"]}
    included = set(policy["roots"])
    for _ in range(len(components)):
        included |= {child for ref in tuple(included) for child in adjacency[ref]}
    assert set(policy["components"]) == included
    assert manifest["roots"] == policy["roots"]
    assert set(manifest["excluded"]) == set(components) - included
    assert manifest["dependencies"] == adjacency
    records = {item["bom_ref"]: item for item in manifest["components"]}
    assert len(records) == len(manifest["components"]) and set(records) == included
    expected = {"inputs/bom.json": bom_bytes, "inputs/approvals.json": policy_bytes}
    total = 0
    for ref in included:
        approved, component, record = policy["components"][ref], components[ref], records[ref]
        artifact = Path(wheels) / approved["artifact"]
        raw = artifact.read_bytes()
        checksum = hashlib.sha256(raw).hexdigest()
        assert checksum == approved["sha256"] == record["artifact_sha256"]
        assert checksum in [h["content"] for h in component["hashes"] if h["alg"] == "SHA-256"]
        assert record["artifact"] == approved["artifact"]
        assert record["name"] == component["name"] and record["version"] == component["version"]
        assert record["choice"] == approved["choice"]
        assert record["expression"] == approved["expression"] == component["licenses"][0]["expression"]
        with zipfile.ZipFile(artifact) as archive:
            metadata_paths = [name for name in archive.namelist() if name.endswith(".dist-info/METADATA")]
            assert len(metadata_paths) == 1
            metadata_path = metadata_paths[0]
            metadata = archive.read(metadata_path)
            headers = Parser(policy=default).parsestr(metadata.decode("utf-8"))
            assert headers["License-Expression"] == approved["expression"]
            assert headers["Name"] == component["name"] and headers["Version"] == component["version"]
            assert record["metadata_path"] == metadata_path
            assert record["metadata_sha256"] == hashlib.sha256(metadata).hexdigest()
            expected[record["metadata_output"]] = metadata
            files = headers.get_all("License-File")
            assert set(files) == set(approved["materials"])
            materials = {entry["license_file"]: entry for entry in record["materials"]}
            assert len(materials) == len(record["materials"]) and set(materials) == set(files)
            for path in files:
                entry = materials[path]
                source_path = metadata_path.rsplit("/", 1)[0] + "/licenses/" + path
                assert entry["source_path"] == source_path
                data = archive.read(source_path)
                assert entry["licenses"] == approved["materials"][path]["licenses"]
                assert entry["bytes"] == len(data)
                assert entry["sha256"] == hashlib.sha256(data).hexdigest() == approved["materials"][path]["sha256"]
                expected[entry["output_path"]] = data
                total += len(data)
    notice = (out / "NOTICE.txt").read_bytes()
    for ref in included:
        assert ref.encode() in notice
        for material in records[ref]["materials"]:
            assert material["output_path"].encode() in notice
    expected["NOTICE.txt"] = notice
    files = {entry["path"]: entry for entry in manifest["files"]}
    assert len(files) == len(manifest["files"]) and set(files) == set(expected)
    consumed = len(manifest_bytes)
    for path, data in expected.items():
        actual = (out / path).read_bytes()
        assert actual == data
        assert files[path]["bytes"] == len(actual)
        assert files[path]["sha256"] == hashlib.sha256(actual).hexdigest()
        consumed += len(actual)
    actual_paths = {path.relative_to(out).as_posix() for path in out.rglob("*") if path.is_file()}
    assert actual_paths == set(expected) | {"manifest.json"}
    return {"components": len(included), "materials": sum(len(r["materials"]) for r in records.values()),
            "material_bytes": total, "consumed_files": len(actual_paths), "consumed_bytes": consumed,
            "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest()}


if __name__ == "__main__":
    print(json.dumps(consume(*sys.argv[1:]), sort_keys=True))

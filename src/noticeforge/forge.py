import os
import tempfile
from pathlib import Path
from .bom import closure
from .contracts import read_bytes, parse_json, keys, unique_strings, safe_path, digest, encoded
from .wheels import collect
from .limits import Limits
from .errors import InputError


def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def forge(bom, approvals, wheel_dir, output, *, limits=None):
    """Publish a NEW notice directory after all supplied approvals/materials agree.

    Inputs are snapshots of trusted local files, never edited. The caller supplies
    human decisions; output attests collection consistency, not legal adequacy.
    A crash can leave an unadvertised sibling staging directory for manual cleanup.
    """
    limits = (limits or Limits()).validate()
    try:
        bom_path, approval_path, wheel_root = (Path(item).resolve(strict=True) for item in (bom, approvals, wheel_dir))
        destination = Path(output).resolve()
        if not wheel_root.is_dir() or destination.exists():
            raise InputError("wheel directory required; output must not exist")
        # Before mkdir: do not create a destination inside any input directory.
        if destination == bom_path or destination == approval_path or destination == wheel_root or wheel_root in destination.parents:
            raise InputError("output aliases or is inside inputs")
        bom_data = read_bytes(bom_path, limits.max_input_bytes)
        approval_data = read_bytes(approval_path, limits.max_input_bytes)
        policy = keys(parse_json(approval_data), ["format", "approved_by", "roots", "components"])
        if policy["format"] != "noticeforge-approvals/v1":
            raise InputError("unsupported approval format")
        from .contracts import text
        text(policy["approved_by"], "human approval identity", 256)
        roots = unique_strings(policy["roots"], "roots", limits.max_components)
        included, excluded, edges = closure(parse_json(bom_data), roots, limits)
        mapping = policy["components"]
        if not isinstance(mapping, dict) or set(mapping) != {item["bom_ref"] for item in included}:
            raise InputError("approval components must equal explicit root closure")
        records, payloads, material_bytes = [], {"inputs/bom.json": bom_data, "inputs/approvals.json": approval_data}, 0
        for component in included:
            approval = mapping[component["bom_ref"]]
            if not isinstance(approval, dict):
                raise InputError("invalid component approval")
            filename = safe_path(approval.get("artifact"))
            if "/" in filename or not filename.endswith(".whl"):
                raise InputError("artifact must be a wheel basename")
            artifact_path = (wheel_root / filename).resolve(strict=True)
            if artifact_path.parent != wheel_root or not artifact_path.is_file():
                raise InputError("wheel artifact escapes directory")
            record = collect(read_bytes(artifact_path, limits.max_archive_bytes), component, approval, limits)
            prefix = "components/" + digest(component["bom_ref"].encode("utf-8"))
            metadata = record.pop("metadata")
            record["metadata_output"] = prefix + "/METADATA"
            record["metadata_sha256"] = digest(metadata)
            payloads[record["metadata_output"]] = metadata
            for material in record["materials"]:
                data = material.pop("data")
                material["output_path"] = prefix + "/licenses/" + material["license_file"]
                payloads[material["output_path"]] = data
                material_bytes += len(data)
            records.append(record)
        if material_bytes > limits.max_material_bytes:
            raise InputError("total material allowance exceeded")
        notice = ["NOTICE material collection", "Human approvals: " + policy["approved_by"],
                  "Collection consistency only; no legal compliance determination.", ""]
        for record in records:
            notice += [record["bom_ref"], f"  {record['name']} {record['version']}",
                       "  Declared: " + record["expression"], "  Approved atoms: " + ", ".join(record["choice"])]
            notice += ["  Material: " + item["output_path"] for item in record["materials"]]
        payloads["NOTICE.txt"] = ("\n".join(notice) + "\n").encode("utf-8")
        manifest = {"format": "noticeforge-bundle/v1", "roots": roots, "excluded": excluded,
                    "dependencies": edges, "components": records,
                    "inputs": {"bom_sha256": digest(bom_data), "approvals_sha256": digest(approval_data)},
                    "files": [{"path": path, "bytes": len(data), "sha256": digest(data)} for path, data in sorted(payloads.items())]}
        payloads["manifest.json"] = encoded(manifest)
        output_bytes = sum(map(len, payloads.values()))
        if output_bytes > limits.max_output_bytes:
            raise InputError("complete output allowance exceeded")
        destination.parent.mkdir(parents=True, exist_ok=True)
        stage = Path(tempfile.mkdtemp(prefix=".noticeforge-stage-", dir=destination.parent))
        # All decisions verified before staging. All bytes verified again before rename.
        for path, data in sorted(payloads.items()):
            _write(stage / path, data)
        for path, data in payloads.items():
            if (stage / path).read_bytes() != data:
                raise InputError("staged material verification failed")
        stage.rename(destination)
        return {"status": "PUBLISHED", "output": str(destination), "components": len(records),
                "materials": sum(len(record["materials"]) for record in records),
                "material_bytes": material_bytes, "output_bytes": output_bytes,
                "manifest_sha256": digest(payloads["manifest.json"])}
    except (OSError, ValueError, TypeError, AttributeError, RecursionError) as exc:
        if isinstance(exc, InputError):
            raise
        raise InputError(f"cannot verify/publish local inputs: {exc}") from exc

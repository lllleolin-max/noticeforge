import base64
import csv
import hashlib
import io
import json
import zipfile
from pathlib import Path


def wheel(path, name="order_app", expression="MIT", materials=None, extra=None):
    materials = materials or {"LICENSE": b"Author-approved lab license material.\n"}
    prefix = name + "-1.0.dist-info"
    metadata = f"Metadata-Version: 2.4\nName: {name}\nVersion: 1.0\nLicense-Expression: {expression}\n"
    metadata += "".join("License-File: " + key + "\n" for key in materials) + "\n"
    files = {prefix + "/METADATA": metadata.encode(), prefix + "/WHEEL": b"Wheel-Version: 1.0\nGenerator: noticeforge-lab\nRoot-Is-Purelib: true\nTag: py3-none-any\n\n",
             name + ".py": b"def invoice(amount):\n    return amount * 2\n"}
    files.update({prefix + "/licenses/" + key: value for key, value in materials.items()})
    files.update(extra or {})
    record = io.StringIO(newline="")
    writer = csv.writer(record)
    for key, data in files.items():
        writer.writerow([key, "sha256=" + base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode(), len(data)])
    writer.writerow([prefix + "/RECORD", "", ""])
    files[prefix + "/RECORD"] = record.getvalue().encode()
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for key, data in files.items():
            archive.writestr(key, data)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def scenario(root, names=("order_app",), edges=None, roots=None, expression="MIT", materials=None):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    wheels = root / "wheels"
    wheels.mkdir()
    components, approvals = [], {}
    materials = materials or {"LICENSE": b"Author-approved lab license material.\n"}
    for name in names:
        artifact = name + "-1.0-py3-none-any.whl"
        checksum = wheel(wheels / artifact, name, expression, materials)
        components.append({"type": "application" if name == names[0] else "library", "bom-ref": name, "name": name, "version": "1.0", "licenses": [{"expression": expression}], "hashes": [{"alg": "SHA-256", "content": checksum}]})
        approvals[name] = {"artifact": artifact, "sha256": checksum, "expression": expression, "choice": ["MIT"],
                           "materials": {key: {"sha256": hashlib.sha256(data).hexdigest(), "licenses": ["MIT"]} for key, data in materials.items()}}
    edges = edges or {name: [] for name in names}
    roots = roots or [names[0]]
    reached = set(roots)
    while True:
        enlarged = reached | {target for ref in reached for target in edges[ref]}
        if enlarged == reached:
            break
        reached = enlarged
    bom = {"bomFormat": "CycloneDX", "specVersion": "1.6", "version": 1, "metadata": {"component": components[0]}, "components": components[1:],
           "dependencies": [{"ref": name, "dependsOn": edges[name]} for name in names]}
    policy = {"format": "noticeforge-approvals/v1", "approved_by": "LAB AUTHOR; not legal advice", "roots": roots, "components": {ref: approvals[ref] for ref in reached}}
    for filename, value in (("bom.json", bom), ("approvals.json", policy)):
        (root / filename).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return root / "bom.json", root / "approvals.json", wheels

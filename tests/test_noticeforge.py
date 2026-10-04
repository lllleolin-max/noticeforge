import json
import tempfile
import unittest
import zipfile
import hashlib
import struct
import os
from pathlib import Path
from noticeforge import forge, Limits, InputError
from noticeforge.expressions import validate_choice
from fixtures import scenario


class Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
    def tearDown(self):
        self.temp.cleanup()
    def test_diamond_cycle_and_unreachable(self):
        inputs = scenario(self.root, ("app", "left", "right", "shared", "dev"), {"app": ["left", "right"], "left": ["shared"], "right": ["shared"], "shared": ["left"], "dev": []})
        result = forge(*inputs, self.root / "out")
        manifest = json.loads((self.root / "out/manifest.json").read_bytes())
        self.assertEqual(result["components"], 4)
        self.assertEqual(manifest["excluded"], ["dev"])
        self.assertEqual(len(list((self.root / "out").rglob("LICENSE"))), 4)
    def test_all_bytes_and_basenames(self):
        materials = {"left/LICENSE": "版权\nline\r\n".encode(), "right/LICENSE": b"different\x00bytes\n"}
        inputs = scenario(self.root, materials=materials)
        forge(*inputs, self.root / "out")
        manifest = json.loads((self.root / "out/manifest.json").read_bytes())
        for entry in manifest["components"][0]["materials"]:
            self.assertEqual((self.root / "out" / entry["output_path"]).read_bytes(), materials[entry["license_file"]])
    def test_material_budget_exact(self):
        inputs = scenario(self.root, materials={"LICENSE": b"12345"})
        with self.assertRaises(InputError):
            forge(*inputs, self.root / "under", limits=Limits(max_material_bytes=4))
        self.assertFalse((self.root / "under").exists())
        forge(*inputs, self.root / "exact", limits=Limits(max_material_bytes=5))
    def test_bad_hash_and_input_unchanged(self):
        inputs = scenario(self.root)
        raw = [path.read_bytes() for path in inputs[:2]]
        policy = json.loads(raw[1])
        policy["components"]["order_app"]["materials"]["LICENSE"]["sha256"] = "0" * 64
        inputs[1].write_text(json.dumps(policy), encoding="utf-8")
        with self.assertRaises(InputError):
            forge(*inputs, self.root / "out")
        self.assertEqual(inputs[0].read_bytes(), raw[0])
        self.assertFalse((self.root / "out").exists())
    def test_duplicate_ref(self):
        inputs = scenario(self.root)
        bom = json.loads(inputs[0].read_bytes())
        bom["components"] = [bom["metadata"]["component"]]
        inputs[0].write_text(json.dumps(bom), encoding="utf-8")
        with self.assertRaises(InputError):
            forge(*inputs, self.root / "out")
    def test_expression_branch_and_exception(self):
        self.assertEqual(validate_choice("(MIT OR Apache-2.0) AND (MIT OR BSD-2-Clause)", ["MIT", "Apache-2.0"]), ["MIT", "Apache-2.0"])
        self.assertEqual(validate_choice("GPL-2.0-only WITH Classpath-exception-2.0 OR MIT", ["GPL-2.0-only WITH Classpath-exception-2.0"]), ["GPL-2.0-only WITH Classpath-exception-2.0"])
        with self.assertRaises(InputError):
            validate_choice("MIT AND Apache-2.0", ["MIT"])
    def test_alias_and_output_exists(self):
        inputs = scenario(self.root)
        for output in (inputs[0], inputs[2] / "output", self.root):
            with self.assertRaises(InputError):
                forge(*inputs, output)
    def test_bad_limits(self):
        inputs = scenario(self.root)
        for cap in (True, 0, -1, 10**500):
            with self.assertRaises(InputError):
                forge(*inputs, self.root / "out", limits=Limits(max_material_bytes=cap))
    def test_legal_folded_metadata_header(self):
        inputs = scenario(self.root, expression="MIT OR Apache-2.0")
        artifact, = inputs[2].glob("*.whl")
        with zipfile.ZipFile(artifact) as archive:
            files = {name: archive.read(name) for name in archive.namelist()}
        for name in files:
            if name.endswith("/METADATA"):
                files[name] = files[name].replace(b"MIT OR Apache-2.0", b"MIT OR\n Apache-2.0")
        with zipfile.ZipFile(artifact, "w") as archive:
            for name, data in files.items(): archive.writestr(name, data)
        checksum = hashlib.sha256(artifact.read_bytes()).hexdigest()
        for path in inputs[:2]:
            value = json.loads(path.read_bytes())
            if "metadata" in value: value["metadata"]["component"]["hashes"][0]["content"] = checksum
            else: value["components"]["order_app"]["sha256"] = checksum
            path.write_text(json.dumps(value), encoding="utf-8")
        self.assertEqual(forge(*inputs, self.root / "out")["status"], "PUBLISHED")
    def test_raw_zip_nul_filename_refused(self):
        inputs = scenario(self.root)
        artifact, = inputs[2].glob("*.whl")
        with zipfile.ZipFile(artifact) as archive:
            files = [(name + "Xbad" if "/licenses/" in name else name, archive.read(name)) for name in archive.namelist()]
        with zipfile.ZipFile(artifact, "w") as archive:
            for name, data in files: archive.writestr(name, data)
        artifact.write_bytes(artifact.read_bytes().replace(b"/licenses/LICENSEXbad", b"/licenses/LICENSE\x00bad"))
        checksum = hashlib.sha256(artifact.read_bytes()).hexdigest()
        for path in inputs[:2]:
            value = json.loads(path.read_bytes())
            if "metadata" in value: value["metadata"]["component"]["hashes"][0]["content"] = checksum
            else: value["components"]["order_app"]["sha256"] = checksum
            path.write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaisesRegex(InputError, "original filename"):
            forge(*inputs, self.root / "out")
        self.assertFalse((self.root / "out").exists())
    def test_case_and_unicode_directory_aliases(self):
        for index, paths in enumerate((("Legal/LICENSE", "legal/AUTHORS"), ("caf\u00e9/LICENSE", "cafe\u0301/AUTHORS"))):
            inputs = scenario(self.root / str(index), materials={paths[0]: b"a", paths[1]: b"b"})
            with self.assertRaisesRegex(InputError, "ancestor alias"):
                forge(*inputs, self.root / ("out" + str(index)))
            self.assertFalse((self.root / ("out" + str(index))).exists())
    def test_corrupt_deflate_controlled(self):
        inputs = scenario(self.root)
        artifact, = inputs[2].glob("*.whl")
        with zipfile.ZipFile(artifact) as archive:
            member = archive.infolist()[0]
        raw = bytearray(artifact.read_bytes())
        name, extra = struct.unpack_from("<HH", raw, member.header_offset + 26)
        offset = member.header_offset + 30 + name + extra
        raw[offset] = (raw[offset] & ~7) | 7
        artifact.write_bytes(raw)
        checksum = hashlib.sha256(raw).hexdigest()
        for path in inputs[:2]:
            value = json.loads(path.read_bytes())
            if "metadata" in value: value["metadata"]["component"]["hashes"][0]["content"] = checksum
            else: value["components"]["order_app"]["sha256"] = checksum
            path.write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaisesRegex(InputError, "cannot verify wheel"):
            forge(*inputs, self.root / "out")
    def test_symlink_wheel_escape(self):
        inputs = scenario(self.root)
        original, = inputs[2].glob("*.whl")
        outside = self.root / "outside.whl"
        outside.write_bytes(original.read_bytes())
        linked = inputs[2] / "linked.whl"
        try:
            linked.symlink_to(outside)
        except OSError as exc:
            if getattr(exc, "winerror", None) == 1314:
                self.skipTest("Windows symlink privilege unavailable")
            raise
        policy = json.loads(inputs[1].read_bytes())
        policy["components"]["order_app"]["artifact"] = linked.name
        inputs[1].write_text(json.dumps(policy), encoding="utf-8")
        with self.assertRaisesRegex(InputError, "escapes directory"):
            forge(*inputs, self.root / "out")


if __name__ == "__main__":
    unittest.main()

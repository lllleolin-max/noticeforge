import io
import stat
import zipfile
import zlib
import lzma
from email.parser import Parser
from email.policy import default
from packaging.utils import canonicalize_name
from packaging.version import Version, InvalidVersion
from .contracts import digest, safe_path, collision_key, text, keys, sha
from .expressions import normalize, tree, leaves, validate_choice
from .errors import InputError


def collect(data, component, approval, limits):
    keys(approval, ["artifact", "sha256", "expression", "choice", "materials"])
    if sha(approval["sha256"]) != digest(data) or component["artifact_sha256"] != digest(data):
        raise InputError("wheel artifact hash disagrees with BOM/approval")
    expression = normalize(approval["expression"])
    if expression != component["expression"]:
        raise InputError("approval expression disagrees with BOM")
    if not isinstance(approval["choice"], list) or not approval["choice"] or len(approval["choice"]) > 64:
        raise InputError("nonempty bounded approved choice required")
    chosen = validate_choice(expression, approval["choice"])
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
        with archive:
            members = archive.infolist()
            if len(members) > limits.max_zip_members:
                raise InputError("ZIP member allowance exceeded")
            seen, nodes, total = {}, {}, 0
            for member in members:
                # ZipInfo.filename can silently truncate a raw NUL filename.
                # Attribution must describe the original archive path exactly.
                if member.orig_filename != member.filename:
                    raise InputError("ZIP original filename was normalized or truncated")
                path = safe_path(member.filename[:-1] if member.is_dir() else member.filename)
                folded = collision_key(path)
                if folded in seen:
                    raise InputError("duplicate/case/Unicode ZIP path collision")
                seen[folded] = path
                parts = path.split("/")
                for position in range(1, len(parts) + 1):
                    prefix = "/".join(parts[:position])
                    directory = position < len(parts) or member.is_dir()
                    key = collision_key(prefix)
                    if key in nodes and nodes[key] != (prefix, directory):
                        raise InputError("ZIP ancestor alias or file/directory collision")
                    nodes[key] = (prefix, directory)
                kind = stat.S_IFMT(member.external_attr >> 16)
                if kind not in {0, stat.S_IFREG, stat.S_IFDIR} or member.flag_bits & 1:
                    raise InputError("nonregular or encrypted ZIP member")
                total += member.file_size
                if member.file_size > limits.max_member_bytes or total > limits.max_uncompressed_bytes:
                    raise InputError("ZIP uncompressed allowance exceeded")
            metadata_paths = [m.filename for m in members if m.filename.endswith(".dist-info/METADATA") and m.filename.count("/") == 1]
            if len(metadata_paths) != 1:
                raise InputError("exactly one top-level wheel METADATA required")
            metadata_path = metadata_paths[0]
            metadata = archive.read(metadata_path)
            # Metadata is UTF-8 email headers. Access through the header registry
            # unfolds legal continuation lines before field contract checks.
            headers = Parser(policy=default).parsestr(metadata.decode("utf-8"))
            if headers.defects:
                raise InputError("malformed wheel metadata headers")
            def single(name):
                values = headers.get_all(name, [])
                if len(values) != 1:
                    raise InputError(f"exactly one {name} required")
                if getattr(values[0], "defects", ()):
                    raise InputError(f"malformed {name} header")
                return text(str(values[0]), name)
            version = single("Metadata-Version")
            if version not in {"2.4", "2.5", "2.6"}:
                raise InputError("supported wheel metadata versions: 2.4, 2.5, 2.6")
            if canonicalize_name(single("Name")) != canonicalize_name(component["name"]):
                raise InputError("wheel distribution name disagrees with BOM")
            if Version(single("Version")) != Version(component["version"]):
                raise InputError("wheel version disagrees with BOM")
            if normalize(single("License-Expression")) != expression or headers.get_all("License"):
                raise InputError("wheel expression disagrees or ambiguous legacy License")
            paths = [safe_path(str(value)) for value in headers.get_all("License-File", [])]
            if not paths or len(set(map(collision_key, paths))) != len(paths):
                raise InputError("missing or colliding License-File paths")
            materials = approval["materials"]
            if not isinstance(materials, dict) or set(materials) != set(paths):
                raise InputError("approval must map every License-File exactly")
            all_atoms = leaves(tree(expression))
            covered, collected = set(), []
            for path in paths:
                entry = keys(materials[path], ["sha256", "licenses"])
                labels = entry["licenses"]
                if not isinstance(labels, list) or not labels or len(labels) > 64:
                    raise InputError("each material needs approved license attribution")
                labels = [normalize(label) for label in labels]
                if len(set(labels)) != len(labels) or not set(labels) <= all_atoms:
                    raise InputError("material attribution is outside declared expression")
                covered.update(labels)
                source_path = metadata_path.rsplit("/", 1)[0] + "/licenses/" + path
                material = archive.read(source_path)
                if digest(material) != sha(entry["sha256"]):
                    raise InputError("material hash disagrees with approval")
                collected.append({"license_file": path, "source_path": source_path,
                                  "sha256": digest(material), "bytes": len(material),
                                  "licenses": labels, "data": material})
            if not set(chosen) <= covered:
                raise InputError("approved choice has no attributed material")
            return {**component, "artifact": approval["artifact"], "choice": chosen,
                    "metadata_version": version, "metadata_path": metadata_path,
                    "metadata": metadata, "materials": collected}
    except (zipfile.BadZipFile, KeyError, UnicodeError, OSError, RuntimeError,
            NotImplementedError, InvalidVersion, zlib.error, lzma.LZMAError, EOFError) as exc:
        raise InputError(f"cannot verify wheel license materials: {exc}") from exc

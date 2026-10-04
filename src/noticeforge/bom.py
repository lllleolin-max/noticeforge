from .contracts import text, keys, unique_strings, sha
from .expressions import normalize
from .errors import InputError


def closure(bom, roots, limits):
    if not isinstance(bom, dict) or bom.get("bomFormat") != "CycloneDX" or bom.get("specVersion") != "1.6":
        raise InputError("only CycloneDX JSON 1.6 is supported")
    if type(bom.get("version")) is not int or bom["version"] < 1:
        raise InputError("invalid BOM document version")
    declared_refs = set()
    def references(value):
        if isinstance(value, dict):
            if "bom-ref" in value:
                ref = text(value["bom-ref"], "global bom-ref", 512)
                if ref in declared_refs:
                    raise InputError("duplicate global bom-ref")
                declared_refs.add(ref)
            for child in value.values():
                references(child)
        elif isinstance(value, list):
            for child in value:
                references(child)
    references(bom)
    if any(bom.get(field) for field in ("services", "compositions", "vulnerabilities", "formulation")):
        raise InputError("unsupported BOM services/compositions/vulnerabilities/formulation")
    items = bom.get("components", [])
    if not isinstance(items, list):
        raise InputError("components must be an array")
    root_component = bom.get("metadata", {}).get("component")
    if root_component is not None:
        items = [root_component] + items
    if not 1 <= len(items) <= limits.max_components:
        raise InputError("component allowance exceeded")
    components = {}
    for component in items:
        if not isinstance(component, dict) or component.get("type") not in {"application", "library"}:
            raise InputError("only flat application/library components are supported")
        if any(component.get(field) for field in ("components", "evidence", "pedigree")):
            raise InputError("nested/evidence/pedigree components are unsupported")
        ref = text(component.get("bom-ref"), "bom-ref", 512)
        if ref in components:
            raise InputError("duplicate bom-ref")
        name = text(component.get("name"), "component name", 128)
        version = text(component.get("version"), "component version", 128)
        licenses = component.get("licenses")
        if not isinstance(licenses, list) or len(licenses) != 1:
            raise InputError("one declared SPDX expression is required per component")
        keys(licenses[0], ["expression"], ["acknowledgement", "bom-ref"])
        if licenses[0].get("acknowledgement", "declared") != "declared":
            raise InputError("only declared licenses are supported")
        expression = normalize(licenses[0]["expression"])
        hashes = component.get("hashes")
        if not isinstance(hashes, list):
            raise InputError("component artifact hashes are required")
        sha_values = [item.get("content") for item in hashes if isinstance(item, dict) and item.get("alg") == "SHA-256"]
        if len(sha_values) != 1:
            raise InputError("exactly one SHA-256 artifact hash required")
        components[ref] = {"bom_ref": ref, "name": name, "version": version,
                           "expression": expression, "artifact_sha256": sha(sha_values[0])}
    if not set(roots) <= components.keys():
        raise InputError("unknown explicit root")
    dependencies = bom.get("dependencies")
    if not isinstance(dependencies, list):
        raise InputError("explicit complete dependency adjacency is required")
    edges = {}
    count = 0
    for item in dependencies:
        keys(item, ["ref", "dependsOn"])
        ref = text(item["ref"], "dependency ref", 512)
        if ref not in components or ref in edges or not isinstance(item["dependsOn"], list):
            raise InputError("unknown/duplicate dependency node")
        targets = item["dependsOn"]
        if len(targets) != len(set(targets)) or any(target not in components for target in targets):
            raise InputError("duplicate/dangling dependency edge")
        edges[ref] = targets
        count += len(targets)
    if set(edges) != set(components) or count > limits.max_edges:
        raise InputError("missing adjacency or edge allowance exceeded")
    included, pending = set(), list(roots)
    while pending:
        ref = pending.pop()
        if ref not in included:
            included.add(ref)
            pending.extend(edges[ref])
    return [components[ref] for ref in sorted(included)], sorted(set(components) - included), edges

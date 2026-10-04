import hashlib
import json
import re
import unicodedata
from pathlib import Path
from .errors import InputError


def digest(data):
    return hashlib.sha256(data).hexdigest()


def text(value, name, cap=4096):
    if not isinstance(value, str) or not value or len(value) > cap or any(ord(c) < 32 for c in value):
        raise InputError(f"invalid {name}")
    return value


def sha(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise InputError("expected lowercase SHA256")
    return value


def keys(value, required, optional=()):
    if not isinstance(value, dict) or not set(required) <= value.keys() or value.keys() - set(required) - set(optional):
        raise InputError(f"expected object fields {sorted(required)}")
    return value


def unique_strings(value, name, cap=1000):
    if not isinstance(value, list) or not 1 <= len(value) <= cap:
        raise InputError(f"invalid {name} list")
    result = [text(item, name) for item in value]
    if len(set(result)) != len(result):
        raise InputError(f"duplicate {name}")
    return result


def safe_path(value):
    text(value, "relative material path", 180)
    if "\\" in value or value.startswith("/"):
        raise InputError("material path must be relative POSIX")
    for part in value.split("/"):
        stem = part.split(".")[0].upper()
        if (part in {"", ".", ".."} or part[-1:] in {".", " "} or
                any(c in part for c in ':<>"|?*') or len(part.encode("utf-8")) > 120 or
                stem in {"CON", "PRN", "AUX", "NUL", *[f"COM{i}" for i in range(1, 10)], *[f"LPT{i}" for i in range(1, 10)]}):
            raise InputError("unsafe portable material path")
    return value


def collision_key(path):
    return unicodedata.normalize("NFC", path).casefold()


def read_bytes(path, cap):
    try:
        with Path(path).open("rb") as stream:
            data = stream.read(cap + 1)
    except OSError as exc:
        raise InputError(f"cannot read input: {exc}") from exc
    if len(data) > cap:
        raise InputError("input byte allowance exceeded")
    return data


def parse_json(data):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise InputError("duplicate JSON object key")
            result[key] = value
        return result
    def constant(value):
        raise InputError(f"nonfinite JSON constant {value}")
    try:
        return json.loads(data.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant)
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise InputError(f"invalid bounded UTF-8 JSON: {exc}") from exc


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")

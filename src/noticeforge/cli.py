import argparse
import json
import sys
from dataclasses import fields
from . import forge, Limits, InputError


def main(argv=None):
    parser = argparse.ArgumentParser(description="Collect approved wheel license bytes; no legal determination")
    parser.add_argument("--version", action="version", version="noticeforge 0.1.0")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("forge")
    for name in ("bom", "approvals", "wheel-dir", "output"):
        build.add_argument("--" + name, required=True)
    for field in fields(Limits()):
        build.add_argument("--" + field.name.replace("_", "-"), type=int, default=field.default)
    args = parser.parse_args(argv)
    try:
        limits = Limits(**{field.name: getattr(args, field.name) for field in fields(Limits())})
        result = forge(args.bom, args.approvals, args.wheel_dir, args.output, limits=limits)
    except InputError as exc:
        print(json.dumps({"status": "REFUSED", "reason": str(exc)}), file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Validate draft or locked medical PPT content packages."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from content_package import ROUTE_TERMS, read_text, validate_document, validate_pair


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="stage", required=True)

    draft = subparsers.add_parser("draft", help="校验客户确认草稿")
    draft.add_argument("customer", type=Path)
    draft.add_argument("--route", required=True, choices=tuple(ROUTE_TERMS))
    draft.add_argument("--mode", required=True, choices=("authorized", "strict", "simulation"))
    draft.add_argument("--outline-card")

    locked = subparsers.add_parser("locked", help="校验冻结客户终版与视觉AI版")
    locked.add_argument("customer", type=Path)
    locked.add_argument("--ai", type=Path, required=True)
    locked.add_argument("--route", required=True, choices=tuple(ROUTE_TERMS))
    locked.add_argument("--mode", required=True, choices=("authorized", "strict", "simulation"))
    locked.add_argument("--outline-card")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.stage == "draft":
        result = validate_document(
            read_text(args.customer),
            stage="draft",
            role="customer",
            route=args.route,
            mode=args.mode,
            outline_card=args.outline_card,
        )
    else:
        result = validate_pair(
            read_text(args.customer),
            read_text(args.ai),
            route=args.route,
            mode=args.mode,
            outline_card=args.outline_card,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

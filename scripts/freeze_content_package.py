#!/usr/bin/env python3
"""Freeze a confirmed customer draft into a same-source customer/visual-AI pair."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from content_package import (
    ROUTE_TERMS,
    extract_top_section,
    field_value,
    make_lock_id,
    read_text,
    validate_document,
    validate_pair,
)


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("customer_draft", type=Path)
    parser.add_argument("--customer-output", type=Path, required=True)
    parser.add_argument("--ai-output", type=Path, required=True)
    parser.add_argument("--date", required=True, help="YYYYMMDD")
    parser.add_argument("--version", required=True, help="vXX")
    parser.add_argument("--confirmation", required=True)
    parser.add_argument("--visual-reference", required=True)
    parser.add_argument("--route", required=True, choices=tuple(ROUTE_TERMS))
    parser.add_argument("--mode", required=True, choices=("authorized", "strict", "simulation"))
    parser.add_argument("--outline-card")
    return parser.parse_args()


def replace_status_field(text: str, field: str, value: str) -> str:
    pattern = rf"(?m)^-\s*{re.escape(field)}[：:].*$"
    replaced, count = re.subn(pattern, f"- {field}：{value}", text, count=1)
    if count != 1:
        raise ValueError(f"没有唯一识别到状态字段：{field}")
    return replaced


def build_locked_customer(
    draft: str, *, date: str, version: str, confirmation: str
) -> tuple[str, str]:
    if not re.fullmatch(r"\d{8}", date):
        raise ValueError("date必须使用YYYYMMDD格式")
    if not re.fullmatch(r"v\d{2}", version):
        raise ValueError("version必须使用vXX格式")
    if not re.search(r"确认|按这版|可以制作", confirmation):
        raise ValueError("confirmation没有表达明确内容确认")

    locked = replace_status_field(draft, "内容状态", "已冻结")
    locked = replace_status_field(locked, "内容版本", version)
    locked = replace_status_field(locked, "确认记录", confirmation)
    lock_id = make_lock_id(locked, date, version)
    locked = replace_status_field(locked, "content_lock_id", lock_id)
    return locked, lock_id


def build_ai_text(customer_text: str, visual_reference: str) -> str:
    body = customer_text
    first_newline = body.find("\n")
    if first_newline >= 0 and not body.startswith("【项目参数】"):
        body = body[first_newline + 1 :].lstrip("\n")
    body = replace_status_field(body, "文档用途", "视觉AI投喂")
    if re.search(r"无参考|未提供", visual_reference):
        reference_instruction = (
            "- 本次未提供视觉参考；不得依据本文件推断或推荐通用风格，视觉方向由使用者另行决定。"
        )
    else:
        reference_instruction = (
            "- 本次随附的PPT模板或效果参考图是唯一视觉效果依据；不得另行建立、混合或套用其他视觉风格。\n"
            "- 请自行学习参考稿的视觉语言、构图方式、信息层级、页面节奏和整体质感，并据此完成设计。"
        )
    template_path = (
        Path(__file__).resolve().parents[1]
        / "assets"
        / "visual-ai-handoff-template.md"
    )
    wrapper = template_path.read_text(encoding="utf-8")
    wrapper = wrapper.replace("{{reference_instruction}}", reference_instruction)
    wrapper = wrapper.replace("{{visual_reference}}", visual_reference.strip())
    return f"{wrapper.strip()}\n\n{body.strip()}\n"


def main() -> int:
    args = parse_args()
    for output in (args.customer_output, args.ai_output):
        if output.exists():
            print(json.dumps({"status": "failed", "errors": [f"输出已存在，禁止覆盖：{output}"]}, ensure_ascii=False, indent=2))
            return 1

    draft = read_text(args.customer_draft)
    draft_result = validate_document(
        draft,
        stage="draft",
        role="customer",
        route=args.route,
        mode=args.mode,
        outline_card=args.outline_card,
    )
    if draft_result["status"] != "passed":
        print(json.dumps({"status": "failed", "phase": "draft_validation", "result": draft_result}, ensure_ascii=False, indent=2))
        return 1
    pending_total = field_value(
        extract_top_section(draft, "【版本与内容状态】"), "待确认项总数"
    )
    if pending_total != "0":
        print(json.dumps({"status": "failed", "errors": ["草稿仍有待确认项，不能冻结"]}, ensure_ascii=False, indent=2))
        return 1
    unresolved_evidence = field_value(
        extract_top_section(draft, "【版本与内容状态】"), "未完成证据项总数"
    )
    evidence_freeze_status = field_value(
        extract_top_section(draft, "【输入资料与补全边界】"), "证据冻结状态"
    )
    if unresolved_evidence != "0":
        print(json.dumps({"status": "failed", "errors": ["草稿仍有未完成证据项，不能冻结"]}, ensure_ascii=False, indent=2))
        return 1
    if evidence_freeze_status != "可冻结":
        print(json.dumps({"status": "failed", "errors": ["证据冻结状态不是“可冻结”，不能冻结"]}, ensure_ascii=False, indent=2))
        return 1

    try:
        customer_text, lock_id = build_locked_customer(
            draft,
            date=args.date,
            version=args.version,
            confirmation=args.confirmation,
        )
        ai_text = build_ai_text(customer_text, args.visual_reference)
    except ValueError as exc:
        print(json.dumps({"status": "failed", "errors": [str(exc)]}, ensure_ascii=False, indent=2))
        return 1

    result = validate_pair(
        customer_text,
        ai_text,
        route=args.route,
        mode=args.mode,
        outline_card=args.outline_card,
    )
    if result["status"] != "passed":
        print(json.dumps({"status": "failed", "phase": "locked_validation", "result": result}, ensure_ascii=False, indent=2))
        return 1

    args.customer_output.parent.mkdir(parents=True, exist_ok=True)
    args.ai_output.parent.mkdir(parents=True, exist_ok=True)
    args.customer_output.write_text(customer_text.rstrip() + "\n", encoding="utf-8")
    args.ai_output.write_text(ai_text.rstrip() + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "passed",
                "content_lock_id": lock_id,
                "customer_output": str(args.customer_output),
                "ai_output": str(args.ai_output),
                "slides": result["customer"]["slides_detected"],
                "boundary": result["boundary"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

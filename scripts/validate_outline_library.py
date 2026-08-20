#!/usr/bin/env python3
"""Validate the v11 medical PPT outline-card library and routing contract."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from content_package import load_outline_cards


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


ROOT = Path(__file__).resolve().parent.parent
CARD_DIR = ROOT / "references" / "outline-cards"
ROUTING_PATH = ROOT / "references" / "outline-routing.md"
SKILL_PATH = ROOT / "SKILL.md"

EXPECTED_IDS = {
    "nursing_round",
    "nursing_teaching_round",
    "nursing_case",
    "pdca_qi",
    "qcc",
    "rca_event",
    "patient_education",
    "nursing_training",
    "research_proposal",
    "research_defense",
    "annual_report",
    "job_competition",
    "evidence_translation",
    "new_technology_project",
}

REQUIRED_HEADINGS = (
    "## 卡片身份",
    "## 适用条件",
    "## 不适用与易混淆",
    "## 必需输入",
    "## 标准目录",
    "## 常见变体",
    "## 页数分配",
    "## 内容闭环",
    "## 典型页面任务",
    "## 禁止伪造",
    "## 外部优先与边界",
)

ALLOWED_BASE_ROUTES = {
    "nursing_case",
    "pdca_qi",
    "medical_teaching",
    "research_defense",
    "outline_custom",
}


def get_outline_cards() -> dict[str, dict[str, object]]:
    return load_outline_cards()


def validate_outline_selection(
    task_section: str,
    logic_section: str,
    route: str,
    card_id: str,
) -> list[str]:
    errors: list[str] = []
    card = get_outline_cards().get(card_id)
    if not card:
        return [f"未知大纲卡ID：{card_id}"]
    base_route = str(card.get("base_content_route"))
    if route != base_route:
        errors.append(f"基础内容路由不一致：大纲卡要求{base_route}，当前为{route}")
    if f"大纲卡ID：{card_id}" not in task_section:
        errors.append(f"任务参数未声明大纲卡ID：{card_id}")
    for requirement in card.get("required_logic_terms", []):
        alternatives = requirement.get("any_of", [])
        if not any(str(term) in logic_section for term in alternatives):
            errors.append(f"内容闭环缺少：{requirement.get('label', '未命名要求')}")
    return errors


def validate_library() -> dict[str, object]:
    errors: list[str] = []
    warnings: list[str] = []
    checked_cards: list[str] = []

    outline_cards = get_outline_cards()
    ids = set(outline_cards)
    missing_ids = sorted(EXPECTED_IDS - ids)
    extra_ids = sorted(ids - EXPECTED_IDS)
    if missing_ids:
        errors.append(f"缺少核心大纲卡：{', '.join(missing_ids)}")
    if extra_ids:
        errors.append(f"出现未登记的核心大纲卡：{', '.join(extra_ids)}")

    routing_text = ROUTING_PATH.read_text(encoding="utf-8")
    skill_text = SKILL_PATH.read_text(encoding="utf-8")
    if "v11.0 大纲路由" not in skill_text:
        errors.append("SKILL.md未声明v11.0大纲路由")

    seen_files: set[str] = set()
    for card_id, card in outline_cards.items():
        filename = card.get("file")
        base_route = card.get("base_content_route")
        if not isinstance(filename, str) or not filename:
            errors.append(f"{card_id}缺少文件名")
            continue
        if filename in seen_files:
            errors.append(f"大纲卡文件名重复：{filename}")
        seen_files.add(filename)
        if base_route not in ALLOWED_BASE_ROUTES:
            errors.append(f"{card_id}基础内容路由无效：{base_route}")

        path = CARD_DIR / filename
        if not path.is_file():
            errors.append(f"{card_id}文件不存在：{filename}")
            continue
        text = path.read_text(encoding="utf-8")
        for heading in REQUIRED_HEADINGS:
            if heading not in text:
                errors.append(f"{card_id}缺少章节：{heading}")
        if f"- 大纲卡ID：`{card_id}`" not in text:
            errors.append(f"{card_id}文件内ID不一致")
        if "- 版本：v11.0" not in text:
            errors.append(f"{card_id}文件内版本不是v11.0")
        if f"- 基础内容路由：`{base_route}`" not in text:
            errors.append(f"{card_id}文件内基础内容路由不一致")
        for page_count in (12, 16, 20, 30):
            allocation_match = re.search(
                rf"(?m)^- {page_count}页：(.*)$",
                text,
            )
            if not allocation_match:
                errors.append(f"{card_id}缺少{page_count}页初始分配")
            else:
                allocated = sum(
                    int(value) for value in re.findall(r"\d+", allocation_match.group(1))
                )
                if allocated != page_count:
                    errors.append(
                        f"{card_id}的{page_count}页初始分配合计为{allocated}页"
                    )
        if len(re.findall(r"(?m)^\d+\. `\d{2} ", text)) < 5:
            errors.append(f"{card_id}标准目录少于5个一级章节")
        if f"`{card_id}`" not in routing_text:
            errors.append(f"路由表未登记{card_id}")

        requirements = card.get("required_logic_terms")
        if not isinstance(requirements, list) or not requirements:
            errors.append(f"{card_id}缺少机器可读闭环要求")
            continue
        synthetic_logic_parts: list[str] = []
        for requirement in requirements:
            if not isinstance(requirement, dict):
                errors.append(f"{card_id}闭环要求格式无效")
                continue
            alternatives = requirement.get("any_of")
            if not isinstance(alternatives, list) or not alternatives:
                errors.append(f"{card_id}闭环要求缺少any_of")
                continue
            synthetic_logic_parts.append(str(alternatives[0]))
        task_section = (
            "- 大纲来源：v11大纲卡\n"
            f"- 大纲卡ID：{card_id}\n"
            "- 大纲卡版本：v11.0\n"
        )
        positive_errors = validate_outline_selection(
            task_section,
            " → ".join(synthetic_logic_parts),
            str(base_route),
            card_id,
        )
        if positive_errors:
            errors.append(f"{card_id}正向路由自检失败：{'；'.join(positive_errors)}")
        negative_errors = validate_outline_selection(
            task_section,
            "",
            str(base_route),
            card_id,
        )
        if not any("内容闭环缺少" in item for item in negative_errors):
            errors.append(f"{card_id}负向闭环未被拦截")
        checked_cards.append(card_id)

    status = "passed" if not errors else "failed"
    return {
        "status": status,
        "schema_version": "v11.0",
        "cards_expected": len(EXPECTED_IDS),
        "cards_checked": len(checked_cards),
        "errors": errors,
        "warnings": warnings,
        "boundary": (
            "本结果只验证v11大纲卡结构、清单、基础路由和闭环拦截；"
            "不验证医学终审、逐页完整文案、内容冻结、视觉生成或最终PPT。"
        ),
    }


def main() -> int:
    try:
        result = validate_library()
    except (OSError, UnicodeError, ValueError, KeyError, json.JSONDecodeError) as exc:
        result = {
            "status": "failed",
            "errors": [str(exc)],
            "warnings": [],
        }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())

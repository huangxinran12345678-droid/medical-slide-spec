#!/usr/bin/env python3
"""Shared parsing, hashing, and validation for medical PPT content packages."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


TOP_SECTIONS = (
    "【项目参数】",
    "【版本与内容状态】",
    "【输入资料与补全边界】",
    "【显式目录与页数分配】",
    "【内容逻辑约束（不作为目录标题）】",
    "【逐页完整内容】",
    "【待确认事项汇总】",
    "【主要资料与医学审核】",
)

VISUAL_CONTROL_PATTERNS = (
    r"【参考模板画像】",
    r"【视觉设计系统】",
    r"【页面设计判定",
    r"(?m)^-\s*页面原型[：:]",
    r"(?m)^-\s*容器策略[：:]",
    r"(?m)^-\s*区域实现[：:]",
    r"(?m)^-\s*区域占比[：:]",
    r"(?m)^-\s*布局与阅读顺序[：:]",
    r"(?m)^-\s*图标预算[：:]",
    r"(?m)^-\s*字体、颜色与强调[：:]",
    r"(?m)^-\s*动画[：:]",
    r"(?m)^-\s*视觉焦点[：:]",
    r"(?im)^\s*[-•·]?\s*(?:制作要求|视觉要求|设计要求|排版要求)[：:].*(?:配色|颜色|字体|字号|版式|布局|容器|区域|分栏|图标|装饰|卡片|圆角|留白|视觉)",
    r"(?im)^\s*[-•·]?\s*(?:本页|页面|请|建议|采用|使用|设置).*?(?:左右分栏|上下分栏|双栏布局|三栏布局|卡片式布局|圆角卡片|区域占比|视觉焦点|(?:蓝色|红色|绿色|深色|浅色|渐变)[^。\n]{0,12}(?:卡片|背景|字体|标题|边框)|图标.*(?:左侧|右侧|上方|下方))",
    r"(?im)^\s*[-•·]?\s*(?:标题|正文|背景|卡片|图标).*?(?:使用|采用|设置|放置|位于).*?(?:颜色|字体|字号|左侧|右侧|上方|下方|渐变|圆角)",
)

PAGE_LIMITS: dict[str, dict[str, int]] = {
    "封面": {"body": 80, "combined": 80, "nodes": 3},
    "目录": {"body": 100, "combined": 100, "nodes": 7},
    "章节过渡": {"body": 60, "combined": 60, "nodes": 2},
    "普通内容": {"body": 220, "combined": 300, "nodes": 6},
    "病例事实": {"body": 240, "combined": 340, "nodes": 8},
    "框架关系": {"body": 180, "combined": 300, "nodes": 7},
    "图表数据": {"body": 140, "combined": 360, "nodes": 6},
    "表格": {"body": 160, "combined": 420, "nodes": 8},
    "操作宣教": {"body": 240, "combined": 340, "nodes": 8},
    "总结": {"body": 160, "combined": 220, "nodes": 4},
    "参考文献": {"body": 520, "combined": 520, "nodes": 12},
    "其他": {"body": 220, "combined": 320, "nodes": 7},
}

ROUTE_TERMS: dict[str, tuple[tuple[str, tuple[str, ...]], ...]] = {
    "nursing_case": (
        ("护理评估", ("护理评估",)),
        ("护理问题", ("护理问题", "护理诊断")),
        ("护理目标", ("护理目标", "目标")),
        ("护理措施", ("护理措施", "循证措施")),
        ("效果评价", ("效果评价", "护理效果", "目标达成")),
    ),
    "pdca_qi": (
        ("指标或基线", ("指标定义", "基线")),
        ("真因验证", ("真因验证",)),
        ("对策实施", ("对策实施", "实施过程")),
        ("过程指标", ("过程指标",)),
        ("标准化", ("标准化", "持续监测")),
    ),
    "medical_teaching": (
        ("学习目标", ("学习目标",)),
        ("知识框架", ("知识框架", "核心知识")),
        ("应用", ("病例应用", "情景应用")),
        ("评价", ("后测", "教学评价", "学习评价")),
    ),
    "research_defense": (
        ("研究缺口", ("研究缺口",)),
        ("研究方法", ("研究方法", "研究设计")),
        ("主要结果", ("主要结果",)),
        ("局限", ("局限",)),
        ("结论", ("研究结论", "结论")),
    ),
    "outline_custom": (),
}

PAGE_HEADING_RE = re.compile(r"(?m)^第\s*(\d+)\s*页\s*[｜|]\s*([^\r\n]+)\s*$")
FIELD_RE_TEMPLATE = r"(?ms)^-\s*{field}[：:]\s*(.*?)(?=^-\s*[^\n：:]+[：:]|\Z)"
LOCK_RE = re.compile(r"^MS-(\d{8})-(v\d{2})-([0-9a-f]{12})$")

EVIDENCE_LEVEL_ORDER = {"E0": 0, "E1": 1, "E2": 2, "E3": 3}
OUTLINE_MIN_EVIDENCE = {
    "research_proposal": "E3",
    "research_defense": "E3",
    "evidence_translation": "E3",
    "new_technology_project": "E2",
}

AI_BOUNDARY_FROZEN_TEXT = (
    "- 以下逐页可见文字为已冻结内容，必须原样使用，不得概括、扩写、删减、改写或调换页面。"
)
AI_BOUNDARY_REFERENCE_ONLY = (
    "- 本次随附的PPT模板或效果参考图是唯一视觉效果依据；不得另行建立、混合或套用其他视觉风格。"
)
AI_BOUNDARY_LEARN_REFERENCE = (
    "- 请自行学习参考稿的视觉语言、构图方式、信息层级、页面节奏和整体质感，并据此完成设计。"
)
AI_BOUNDARY_IGNORE_RESIDUE = (
    "- 如果文字文件中仍残留颜色、字体、字号、版式、容器、区域比例、图形、图标或装饰说明，一律忽略。"
)
AI_BOUNDARY_NO_REFERENCE = (
    "- 本次未提供视觉参考；不得依据本文件推断或推荐通用风格，视觉方向由使用者另行决定。"
)
AI_BOUNDARY_NO_REVERSE_EDIT = "- 视觉参考变化不得反向修改冻结内容。"
AI_BOUNDARY_REPORT_CONFLICT = (
    "- 若冻结内容与视觉空间冲突，报告具体页码，不得擅自修改文字、数字、单位、来源或页序。"
)


def normalize_text(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def read_text(path: Path) -> str:
    return normalize_text(path.read_text(encoding="utf-8-sig"))


def clean_value(value: str) -> str:
    lines = [line.rstrip() for line in normalize_text(value).splitlines()]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines)


def is_none_value(value: str) -> bool:
    compact = re.sub(r"\s+", "", value)
    return compact in {"", "无", "不使用", "本页不使用", "不适用", "0"}


def evidence_level_code(value: str) -> str:
    match = re.match(r"^\s*(E[0-3])(?:\s|$|[-—:：])", value, re.I)
    return match.group(1).upper() if match else ""


def extract_top_section(text: str, heading: str) -> str:
    normalized = normalize_text(text)
    start = normalized.find(heading)
    if start < 0:
        return ""
    content_start = start + len(heading)
    ends = [
        normalized.find(other, content_start)
        for other in TOP_SECTIONS
        if other != heading and normalized.find(other, content_start) >= 0
    ]
    end = min(ends) if ends else len(normalized)
    return normalized[content_start:end].strip()


def field_value(section: str, field: str) -> str:
    pattern = FIELD_RE_TEMPLATE.format(field=re.escape(field))
    match = re.search(pattern, section)
    return clean_value(match.group(1)) if match else ""


def page_blocks(text: str) -> list[dict[str, Any]]:
    payload = extract_top_section(text, "【逐页完整内容】")
    matches = list(PAGE_HEADING_RE.finditer(payload))
    pages: list[dict[str, Any]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(payload)
        pages.append(
            {
                "number": int(match.group(1)),
                "title": match.group(2).strip(),
                "block": payload[match.end() : end].strip(),
            }
        )
    return pages


def extract_subsection(block: str, heading: str, next_heading: str | None) -> str:
    start = block.find(heading)
    if start < 0:
        return ""
    start += len(heading)
    end = block.find(next_heading, start) if next_heading else -1
    if end < 0:
        end = len(block)
    return block[start:end].strip()


def canonical_payload(text: str) -> str:
    canonical_pages: list[str] = []
    for page in page_blocks(text):
        visible = extract_subsection(
            page["block"], "【页面可见内容】", "【内容说明（不进入PPT）】"
        )
        lines = [line.rstrip() for line in clean_value(visible).splitlines()]
        canonical_pages.append(
            f"第{page['number']}页｜{page['title']}\n" + "\n".join(lines)
        )
    return "\n\n".join(canonical_pages)


def content_digest(text: str) -> str:
    return hashlib.sha256(canonical_payload(text).encode("utf-8")).hexdigest()[:12]


def make_lock_id(text: str, date: str, version: str) -> str:
    return f"MS-{date}-{version}-{content_digest(text)}"


def visible_char_count(value: str) -> int:
    return len(re.sub(r"[\s|•·*-]", "", value))


def count_nodes(body: str, takeaway: str) -> int:
    bullets = re.findall(r"(?m)^\s*[•·*-]\s+\S", body)
    count = len(bullets)
    if not is_none_value(takeaway):
        count += 1
    return count


def validate_markdown_table(number: int, table: str) -> tuple[list[str], int, int]:
    if is_none_value(table):
        return [], 0, 0
    errors: list[str] = []
    rows = [line.strip() for line in table.splitlines() if line.strip().startswith("|")]
    if len(rows) < 3:
        return [f"第{number}页表格未提供完整Markdown表头、分隔行和数据行"], 0, 0
    widths = [len([cell for cell in row.strip("|").split("|")]) for row in rows]
    if len(set(widths)) != 1:
        errors.append(f"第{number}页表格各行列数不一致：{widths}")
    if not re.fullmatch(r"\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?", rows[1]):
        errors.append(f"第{number}页表格第2行不是Markdown分隔行")
    if re.search(r"(?i)待补|同上|略|todo|tbd", table):
        errors.append(f"第{number}页表格仍有不完整单元格")
    return errors, widths[0] if widths else 0, max(len(rows) - 2, 0)


def validate_chart_data(number: int, chart: str) -> list[str]:
    if is_none_value(chart):
        return []
    errors: list[str] = []
    required = (
        "数据关系",
        "分类或时间",
        "系列",
        "数值",
        "单位",
        "样本量或统计口径",
        "数据来源",
    )
    def nested_value(label: str) -> str:
        match = re.search(
            rf"(?m)^\s*[•·-]\s*{re.escape(label)}[：:]\s*(.+)$", chart
        )
        return clean_value(match.group(1)) if match else ""

    for field in required:
        value = nested_value(field)
        if not value or is_none_value(value):
            errors.append(f"第{number}页图表数据缺少：{field}")
    if not re.search(r"\d", nested_value("数值")):
        errors.append(f"第{number}页图表“数值”未识别到具体数字")
    return errors


def load_outline_cards() -> dict[str, dict[str, Any]]:
    manifest = (
        Path(__file__).resolve().parents[1]
        / "references"
        / "outline-cards"
        / "manifest.json"
    )
    data = json.loads(manifest.read_text(encoding="utf-8"))
    return {card["id"]: card for card in data["cards"]}


def validate_route(text: str, route: str, outline_card: str | None) -> list[str]:
    errors: list[str] = []
    logic = extract_top_section(text, "【内容逻辑约束（不作为目录标题）】")
    if "不得直接替代目录标题" not in logic:
        errors.append("内容逻辑约束未声明不得直接替代目录标题")
    for label, alternatives in ROUTE_TERMS[route]:
        if not any(term in logic for term in alternatives):
            errors.append(f"主路由内容逻辑缺少：{label}")
    if outline_card:
        cards = load_outline_cards()
        card = cards.get(outline_card)
        if not card:
            errors.append(f"未知大纲卡ID：{outline_card}")
        else:
            if card["base_content_route"] != route:
                errors.append(
                    f"大纲卡{outline_card}的基础路由应为{card['base_content_route']}，当前为{route}"
                )
            for item in card["required_logic_terms"]:
                if not any(term in logic for term in item["any_of"]):
                    errors.append(f"大纲卡{outline_card}内容逻辑缺少：{item['label']}")
    return errors


def scan_content_sections(text: str) -> str:
    return "\n".join(extract_top_section(text, heading) for heading in TOP_SECTIONS)


def extract_wrapper_section(text: str, heading: str, end_marker: str) -> str:
    normalized = normalize_text(text)
    start = normalized.find(heading)
    if start < 0:
        return ""
    start += len(heading)
    end = normalized.find(end_marker, start)
    if end < 0:
        end = len(normalized)
    return normalized[start:end].strip()


def validate_visual_ai_boundary(text: str) -> list[str]:
    errors: list[str] = []
    boundary = extract_wrapper_section(
        text, "【视觉AI执行边界】", "【视觉参考状态】"
    )
    if not boundary:
        return ["视觉AI文件缺少最小执行边界"]

    common_requirements = (
        (AI_BOUNDARY_FROZEN_TEXT, "视觉AI边界未要求冻结文字原样使用"),
        (AI_BOUNDARY_IGNORE_RESIDUE, "视觉AI边界未要求忽略残留视觉微操"),
        (AI_BOUNDARY_NO_REVERSE_EDIT, "视觉AI边界未禁止视觉参考反向修改内容"),
        (AI_BOUNDARY_REPORT_CONFLICT, "视觉AI边界未要求内容冲突时只报告页码"),
    )
    for sentence, message in common_requirements:
        if sentence not in boundary:
            errors.append(message)

    reference_status = extract_wrapper_section(
        text, "【视觉参考状态】", "以下内容由冻结脚本"
    )
    if not reference_status:
        errors.append("视觉AI文件缺少视觉参考状态")
        return errors

    no_reference = bool(re.search(r"无参考|未提供", reference_status))
    if no_reference:
        if AI_BOUNDARY_NO_REFERENCE not in boundary:
            errors.append("无参考时未声明不得推断或推荐通用风格")
        if AI_BOUNDARY_REFERENCE_ONLY in boundary or AI_BOUNDARY_LEARN_REFERENCE in boundary:
            errors.append("无参考时不得要求学习或套用不存在的参考稿")
    else:
        if AI_BOUNDARY_REFERENCE_ONLY not in boundary:
            errors.append("有参考时未声明参考稿是唯一视觉效果依据")
        if AI_BOUNDARY_LEARN_REFERENCE not in boundary:
            errors.append("有参考时未要求学习参考稿的视觉语言与整体质感")
    return errors


def validate_document(
    text: str,
    *,
    stage: str,
    role: str,
    route: str,
    mode: str,
    outline_card: str | None = None,
) -> dict[str, Any]:
    normalized = normalize_text(text)
    errors: list[str] = []
    warnings: list[str] = []
    metrics: list[dict[str, Any]] = []

    for heading in TOP_SECTIONS:
        if heading not in normalized:
            errors.append(f"缺少固定章节：{heading}")
    if re.search(r"\{\{[^{}]+\}\}", normalized):
        errors.append("仍有未替换模板变量")

    scan_text = scan_content_sections(normalized)
    for pattern in VISUAL_CONTROL_PATTERNS:
        if re.search(pattern, scan_text):
            errors.append(f"检测到已退出的视觉控制字段：{pattern}")

    params = extract_top_section(normalized, "【项目参数】")
    status_section = extract_top_section(normalized, "【版本与内容状态】")
    boundary_section = extract_top_section(normalized, "【输入资料与补全边界】")
    review_section = extract_top_section(normalized, "【主要资料与医学审核】")
    purpose = field_value(status_section, "文档用途")
    status = field_value(status_section, "内容状态")
    version = field_value(status_section, "内容版本")
    lock_id = field_value(status_section, "content_lock_id")
    confirmation = field_value(status_section, "确认记录")
    pending_count_raw = field_value(status_section, "待确认项总数")
    unresolved_evidence_raw = field_value(status_section, "未完成证据项总数")
    evidence_level_raw = field_value(boundary_section, "证据等级")
    evidence_level = evidence_level_code(evidence_level_raw)
    evidence_level_rationale = field_value(boundary_section, "证据等级判定依据")
    claims_requiring_verification = field_value(boundary_section, "必须核验的医学主张")
    web_permission = field_value(boundary_section, "联网许可")
    web_status = field_value(boundary_section, "联网核验状态")
    evidence_freeze_status = field_value(boundary_section, "证据冻结状态")

    if role == "customer" and purpose != "客户确认":
        errors.append("客户文件的文档用途必须为“客户确认”")
    if role == "ai" and purpose != "视觉AI投喂":
        errors.append("视觉AI文件的文档用途必须为“视觉AI投喂”")
    if not re.fullmatch(r"v\d{2}", version):
        errors.append("内容版本必须使用vXX格式")
    try:
        declared_pending = int(pending_count_raw)
    except ValueError:
        declared_pending = -1
        errors.append("待确认项总数必须是整数")
    try:
        declared_unresolved_evidence = int(unresolved_evidence_raw)
    except ValueError:
        declared_unresolved_evidence = -1
        errors.append("未完成证据项总数必须是整数")

    if not evidence_level:
        errors.append("证据等级必须使用E0、E1、E2或E3")
    if not evidence_level_rationale:
        errors.append("缺少证据等级判定依据")
    if not claims_requiring_verification:
        errors.append("缺少必须核验的医学主张字段")
    if not any(term in web_permission for term in ("已允许", "未允许", "不需要")):
        errors.append("联网许可必须写明“已允许”“未允许”或“不需要”")
    if not web_status:
        errors.append("缺少联网核验状态")
    if evidence_freeze_status not in {"可冻结", "阻断"}:
        errors.append("证据冻结状态必须为“可冻结”或“阻断”")

    minimum_level = "E0"
    if route == "research_defense":
        minimum_level = "E3"
    if outline_card in OUTLINE_MIN_EVIDENCE:
        minimum_level = OUTLINE_MIN_EVIDENCE[outline_card]
    if evidence_level and EVIDENCE_LEVEL_ORDER[evidence_level] < EVIDENCE_LEVEL_ORDER[minimum_level]:
        errors.append(
            f"当前路由/大纲卡的证据等级不得低于{minimum_level}，当前为{evidence_level}"
        )

    if stage == "draft":
        if status != "待确认":
            errors.append("草稿内容状态必须为“待确认”")
        if lock_id != "待确认":
            errors.append("草稿content_lock_id必须为“待确认”")
        if confirmation != "未确认":
            errors.append("草稿确认记录必须为“未确认”")
    else:
        if status != "已冻结":
            errors.append("冻结文件内容状态必须为“已冻结”")
        if not LOCK_RE.fullmatch(lock_id):
            errors.append("冻结文件content_lock_id格式错误")
        if confirmation in {"", "未确认", "待确认"}:
            errors.append("冻结文件缺少明确确认记录")

    page_count_match = re.search(r"(?m)^-\s*页数[：:]\s*(\d+)\s*页", params)
    pages = page_blocks(normalized)
    if not pages:
        errors.append("没有识别到逐页完整内容")
    numbers = [page["number"] for page in pages]
    if numbers != list(range(1, len(numbers) + 1)):
        errors.append(f"页码不连续：{numbers}")
    if page_count_match and int(page_count_match.group(1)) != len(pages):
        errors.append(
            f"项目参数页数为{page_count_match.group(1)}，实际识别到{len(pages)}页"
        )
    elif not page_count_match:
        errors.append("项目参数缺少具体页数")

    actual_pending = 0
    actual_unresolved_evidence = 0
    for page in pages:
        number = page["number"]
        title = page["title"]
        block = page["block"]
        visible = extract_subsection(
            block, "【页面可见内容】", "【内容说明（不进入PPT）】"
        )
        notes = extract_subsection(block, "【内容说明（不进入PPT）】", None)
        if not visible:
            errors.append(f"第{number}页缺少页面可见内容")
        if not notes:
            errors.append(f"第{number}页缺少内容说明")

        required_visible = ["正文", "核心结论", "表格", "图表数据", "来源脚注"]
        if number == 1:
            required_visible = ["主标题", "副标题"] + required_visible
            if title != "封面":
                errors.append("第1页页码行必须写“第1页｜封面”")
        elif re.search(r"(?m)^-\s*(?:主标题|副标题|页面标题|页面副标题)[：:]", visible):
            errors.append(f"第{number}页出现独立标题或副标题字段")

        for field in required_visible:
            if not field_value(visible, field):
                errors.append(f"第{number}页页面可见内容缺少：{field}")
        for field in ("所属目录章节", "页面类型", "页面任务", "内容性质", "证据状态", "待确认项", "不得改动"):
            if not field_value(notes, field):
                errors.append(f"第{number}页内容说明缺少：{field}")

        body = field_value(visible, "正文")
        takeaway = field_value(visible, "核心结论")
        table = field_value(visible, "表格")
        chart = field_value(visible, "图表数据")
        source = field_value(visible, "来源脚注")
        pending = field_value(notes, "待确认项")
        page_evidence_status = field_value(notes, "证据状态")
        page_type = field_value(notes, "页面类型")

        if not source:
            errors.append(f"第{number}页缺少来源脚注")
        if not pending or not is_none_value(pending):
            actual_pending += 1
        if stage == "locked" and not is_none_value(pending):
            errors.append(f"第{number}页仍有待确认项，不能冻结")
        if "待核验" in page_evidence_status:
            actual_unresolved_evidence += 1
            if stage == "locked":
                errors.append(f"第{number}页证据状态仍为待核验，不能冻结")

        table_errors, columns, rows = validate_markdown_table(number, table)
        errors.extend(table_errors)
        errors.extend(validate_chart_data(number, chart))

        if page_type not in PAGE_LIMITS:
            errors.append(f"第{number}页页面类型无效：{page_type}")
            limits = PAGE_LIMITS["其他"]
        else:
            limits = PAGE_LIMITS[page_type]
        body_chars = visible_char_count(body)
        if not is_none_value(takeaway):
            body_chars += visible_char_count(takeaway)
        data_chars = 0
        if not is_none_value(table):
            data_chars += visible_char_count(table)
        if not is_none_value(chart):
            data_chars += visible_char_count(chart)
        combined = body_chars + data_chars
        nodes = count_nodes(body, takeaway)
        if body_chars > limits["body"]:
            errors.append(
                f"第{number}页正文与结论{body_chars}字符，超过{page_type}上限{limits['body']}"
            )
        if combined > limits["combined"]:
            errors.append(
                f"第{number}页正文与数据共{combined}字符，超过{page_type}上限{limits['combined']}"
            )
        if nodes > limits["nodes"]:
            errors.append(
                f"第{number}页内容节点{nodes}个，超过{page_type}上限{limits['nodes']}"
            )
        if columns > 6 or rows > 7:
            errors.append(f"第{number}页表格为{columns}列×{rows}行，超过6列×7行")
        if number > 1 and not is_none_value(body) and body_chars < 20 and page_type not in {
            "目录",
            "章节过渡",
            "参考文献",
        }:
            warnings.append(f"第{number}页正文可能仍接近提纲，需复核是否为完整可见文案")
        metrics.append(
            {
                "page": number,
                "type": page_type,
                "body_chars": body_chars,
                "data_chars": data_chars,
                "combined_chars": combined,
                "nodes": nodes,
                "table_columns": columns,
                "table_rows": rows,
            }
        )

    if declared_pending != actual_pending:
        errors.append(
            f"待确认项总数声明为{declared_pending}，逐页实际识别为{actual_pending}"
        )
    if stage == "locked" and declared_pending != 0:
        errors.append("冻结文件待确认项总数必须为0")
    if declared_unresolved_evidence != actual_unresolved_evidence:
        errors.append(
            f"未完成证据项总数声明为{declared_unresolved_evidence}，逐页实际识别为{actual_unresolved_evidence}"
        )
    if stage == "locked":
        if declared_unresolved_evidence != 0:
            errors.append("冻结文件未完成证据项总数必须为0")
        if evidence_freeze_status != "可冻结":
            errors.append("冻结文件证据冻结状态必须为“可冻结”")
        if re.search(r"待核验|未完成|未授权", web_status):
            errors.append("冻结文件联网核验状态仍未完成")

    web_verified = bool(
        re.search(r"已联网核验", web_status)
        and re.search(r"\d{4}-\d{2}-\d{2}", web_status)
    )
    if evidence_level in {"E2", "E3"}:
        if is_none_value(claims_requiring_verification):
            errors.append(f"{evidence_level}必须逐项列出需要核验的医学主张")
        if stage == "draft" and not web_verified:
            if evidence_freeze_status != "阻断":
                errors.append(f"{evidence_level}未完成联网核验时证据冻结状态必须为“阻断”")
            if declared_unresolved_evidence == 0:
                errors.append(f"{evidence_level}未完成联网核验时必须保留具体待核验证据项")
        if stage == "locked":
            if "已允许" not in web_permission:
                errors.append(f"{evidence_level}冻结前必须取得当次联网许可")
            if not web_verified:
                errors.append(f"{evidence_level}冻结前必须完成带检索日期的当次联网核验")
            retrieval_date = field_value(review_section, "检索日期")
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", retrieval_date):
                errors.append(f"{evidence_level}冻结文件必须记录YYYY-MM-DD格式的检索日期")

    if stage == "locked" and evidence_level == "E3":
        claim_map = field_value(review_section, "核心主张证据映射")
        if is_none_value(claim_map):
            errors.append("E3冻结文件必须提供核心主张证据映射")
        else:
            if not re.search(r"DOI|PMID|https?://", claim_map, re.I):
                errors.append("E3核心主张证据映射必须包含DOI、PMID或官方URL")
            if "支持" not in claim_map:
                errors.append("E3核心主张证据映射必须说明来源与主张的支持关系")

    errors.extend(validate_route(normalized, route, outline_card))
    mode_terms = {
        "authorized": ("授权补全", "建议补全-待核实"),
        "strict": ("真实资料严格",),
        "simulation": ("完整模拟", "模拟"),
    }
    for term in mode_terms[mode]:
        if term not in normalized:
            errors.append(f"补全模式缺少必要声明：{term}")

    if role == "customer" and re.search(
        r"【视觉AI执行边界】|请直接依据上述内容生成完整PPT|不要重新概括大纲",
        normalized,
        re.I,
    ):
        errors.append("客户文件出现视觉AI执行命令")
    if role == "ai":
        errors.extend(validate_visual_ai_boundary(normalized))

    if stage == "locked" and LOCK_RE.fullmatch(lock_id):
        expected = make_lock_id(normalized, LOCK_RE.fullmatch(lock_id).group(1), version)
        if lock_id != expected:
            errors.append(f"content_lock_id与逐页可见内容不一致，应为{expected}")

    return {
        "status": "passed" if not errors else "failed",
        "stage": stage,
        "role": role,
        "route": route,
        "outline_card": outline_card,
        "mode": mode,
        "slides_detected": len(pages),
        "content_digest": content_digest(normalized) if pages else None,
        "errors": errors,
        "warnings": warnings,
        "pages": metrics,
        "evidence_level": evidence_level or None,
        "unresolved_evidence": actual_unresolved_evidence,
        "boundary": "只验证文字包结构、内容密度、证据门禁字段、真实性声明和内容锁；不自动证明文献真实或支持主张，也不验证医学终审、视觉效果、PPT可编辑性或客户验收。",
    }


def validate_pair(
    customer_text: str,
    ai_text: str,
    *,
    route: str,
    mode: str,
    outline_card: str | None = None,
) -> dict[str, Any]:
    customer = validate_document(
        customer_text,
        stage="locked",
        role="customer",
        route=route,
        mode=mode,
        outline_card=outline_card,
    )
    ai = validate_document(
        ai_text,
        stage="locked",
        role="ai",
        route=route,
        mode=mode,
        outline_card=outline_card,
    )
    pair_errors: list[str] = []
    if canonical_payload(customer_text) != canonical_payload(ai_text):
        pair_errors.append("客户终版与视觉AI版逐页可见内容不一致")
    customer_lock = field_value(
        extract_top_section(customer_text, "【版本与内容状态】"), "content_lock_id"
    )
    ai_lock = field_value(
        extract_top_section(ai_text, "【版本与内容状态】"), "content_lock_id"
    )
    customer_version = field_value(
        extract_top_section(customer_text, "【版本与内容状态】"), "内容版本"
    )
    ai_version = field_value(
        extract_top_section(ai_text, "【版本与内容状态】"), "内容版本"
    )
    if customer_lock != ai_lock:
        pair_errors.append("客户终版与视觉AI版content_lock_id不一致")
    if customer_version != ai_version:
        pair_errors.append("客户终版与视觉AI版内容版本不一致")
    all_errors = customer["errors"] + ai["errors"] + pair_errors
    return {
        "status": "passed" if not all_errors else "failed",
        "customer": customer,
        "ai": ai,
        "pair_errors": pair_errors,
        "boundary": customer["boundary"],
    }

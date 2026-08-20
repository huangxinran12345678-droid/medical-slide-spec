#!/usr/bin/env python3
"""Regression tests for v12 content-only packages and content locks."""

from __future__ import annotations

import unittest

from content_package import content_digest, validate_document, validate_pair
from freeze_content_package import build_ai_text, build_locked_customer


DRAFT = """医学PPT逐页内容客户确认稿

【项目参数】

- 项目名称：护理查房测试
- PPT类型：护理查房
- 主题：去标识化神经内科病例护理查房
- 使用场景：科室内部查房
- 核心受众：临床护士
- 汇报目的：形成共同护理判断
- 页数：3页
- 汇报时长：5分钟
- 大纲来源：v11大纲卡
- 大纲卡ID：nursing_round
- 基础内容路由：nursing_case
- 语言：简体中文

【版本与内容状态】

- 文档用途：客户确认
- 内容状态：待确认
- 内容版本：v01
- content_lock_id：待确认
- 确认记录：未确认
- 待确认项总数：0
- 未完成证据项总数：0

【输入资料与补全边界】

- 客户已提供资料：去标识化病例摘要
- 内容补全模式：授权补全
- 建议补全范围：建议补全-待核实内容已标明并在本测试中清零
- 禁止改写内容：诊断、时间、数据和来源
- 证据等级：E1 常规医学内容
- 证据等级判定依据：仅整理客户病例事实，不含现行指南、剂量、阈值或科研主张
- 必须核验的医学主张：无
- 联网许可：不需要
- 联网核验状态：不需要（仅使用客户事实，无时效性外部医学主张）
- 证据冻结状态：可冻结
- 隐私处理：已去标识化
- 医学审核要求：正式使用前由专科护士审核
- 参考文件用途：视觉参考
- 制作参考状态：由制作方另行处理

【显式目录与页数分配】

- 前置页：第1页封面；第2页目录
- 01 护理评估与措施：第3页

目录页只显示：01 护理评估与措施

【内容逻辑约束（不作为目录标题）】

以下闭环不得直接替代目录标题：疾病知识 → 病例介绍与病例时间线 → 护理评估 → 护理问题及护理诊断 → 护理目标 → 护理措施与循证措施 → 动态监测 → 效果评价与目标达成 → 床边查体 → 病例讨论与护长总结。

【逐页完整内容】

第1页｜封面

【页面可见内容】
- 主标题：去标识化神经内科病例护理查房
- 副标题：无
- 正文：
  • 汇报者：测试护士；科室：神经内科
- 核心结论：无
- 表格：无
- 图表数据：无
- 来源脚注：本页无外部医学主张

【内容说明（不进入PPT）】
- 所属目录章节：前置页
- 页面类型：封面
- 页面任务：识别查房主题与汇报身份
- 内容性质：客户已提供
- 证据状态：不涉及外部医学主张
- 待确认项：无
- 不得改动：主题和科室

第2页｜目录

【页面可见内容】
- 正文：
  • 01 护理评估与措施
- 核心结论：无
- 表格：无
- 图表数据：无
- 来源脚注：本页无外部医学主张

【内容说明（不进入PPT）】
- 所属目录章节：前置页
- 页面类型：目录
- 页面任务：说明本次查房内容范围
- 内容性质：客户已提供
- 证据状态：不涉及外部医学主张
- 待确认项：无
- 不得改动：目录名称

第3页｜护理评估与措施

【页面可见内容】
- 正文：
  • 护理评估显示患者存在跌倒风险和吞咽风险，需要持续复评。
  • 护理措施包括环境安全核查、进食前评估和异常情况及时上报。
  • 效果评价使用同一风险指标，记录变化时间、处置动作和复评结果。
- 核心结论：评估、措施、监测与效果必须使用可追溯的同一组指标。
- 表格：无
- 图表数据：无
- 来源脚注：客户去标识化病例摘要，测试资料

【内容说明（不进入PPT）】
- 所属目录章节：01 护理评估与措施
- 页面类型：普通内容
- 页面任务：说明护理风险与闭环措施
- 内容性质：客户已提供；授权补全边界已声明
- 证据状态：客户事实
- 待确认项：无
- 不得改动：风险名称、措施与来源

【待确认事项汇总】

无

【主要资料与医学审核】

- 客户资料：去标识化病例摘要
- 指南、共识、论文或制度：本测试不涉及外部医学主张
- 检索日期：无
- 核心主张证据映射：无
- 仍待医学审核：正式使用前由专科护士审核
- 版本确认方式：只有明确内容确认后才冻结
"""


class ContentPackageTests(unittest.TestCase):
    def validate_draft(self, text: str = DRAFT) -> dict:
        return validate_document(
            text,
            stage="draft",
            role="customer",
            route="nursing_case",
            mode="authorized",
            outline_card="nursing_round",
        )

    def test_complete_content_only_draft_passes(self) -> None:
        result = self.validate_draft()
        self.assertEqual(result["errors"], [])

    def test_locked_pair_is_same_source(self) -> None:
        customer, _ = build_locked_customer(
            DRAFT,
            date="20260816",
            version="v01",
            confirmation="客户已明确确认，按这版做",
        )
        ai = build_ai_text(customer, "5张效果参考图由使用者另行提供")
        result = validate_pair(
            customer,
            ai,
            route="nursing_case",
            mode="authorized",
            outline_card="nursing_round",
        )
        self.assertEqual(result["status"], "passed")

    def test_one_character_change_breaks_lock(self) -> None:
        customer, _ = build_locked_customer(
            DRAFT,
            date="20260816",
            version="v01",
            confirmation="客户已明确确认，按这版做",
        )
        ai = build_ai_text(customer, "另行提供")
        tampered = ai.replace("跌倒风险", "坠床风险", 1)
        result = validate_pair(
            customer,
            tampered,
            route="nursing_case",
            mode="authorized",
            outline_card="nursing_round",
        )
        self.assertEqual(result["status"], "failed")
        self.assertTrue(any("逐页可见内容不一致" in item for item in result["pair_errors"]))

    def test_visual_reference_change_does_not_change_digest(self) -> None:
        customer, _ = build_locked_customer(
            DRAFT,
            date="20260816",
            version="v01",
            confirmation="客户已明确确认，按这版做",
        )
        ai_a = build_ai_text(customer, "5张效果参考图")
        ai_b = build_ai_text(customer, "本次无参考")
        self.assertEqual(content_digest(ai_a), content_digest(ai_b))
        self.assertIn("不得依据本文件推断或推荐通用风格", ai_b)
        self.assertNotIn("唯一视觉效果依据", ai_b)
        self.assertNotIn("请自行学习参考稿", ai_b)
        result = validate_pair(
            customer,
            ai_b,
            route="nursing_case",
            mode="authorized",
            outline_card="nursing_round",
        )
        self.assertEqual(result["status"], "passed")

    def test_reference_handoff_uses_reference_as_only_visual_authority(self) -> None:
        customer, _ = build_locked_customer(
            DRAFT,
            date="20260816",
            version="v01",
            confirmation="客户已明确确认，按这版做",
        )
        ai = build_ai_text(customer, "5张效果参考图由使用者另行提供")
        self.assertIn("唯一视觉效果依据", ai)
        self.assertIn("不得另行建立、混合或套用其他视觉风格", ai)
        self.assertIn("请自行学习参考稿的视觉语言、构图方式、信息层级、页面节奏和整体质感", ai)
        self.assertIn("一律忽略", ai)
        self.assertNotIn("由视觉AI自行处理", ai)

    def test_missing_reference_authority_fails(self) -> None:
        customer, _ = build_locked_customer(
            DRAFT,
            date="20260816",
            version="v01",
            confirmation="客户已明确确认，按这版做",
        )
        ai = build_ai_text(customer, "5张效果参考图由使用者另行提供")
        ai = ai.replace(
            "- 本次随附的PPT模板或效果参考图是唯一视觉效果依据；不得另行建立、混合或套用其他视觉风格。\n",
            "",
            1,
        )
        result = validate_pair(
            customer,
            ai,
            route="nursing_case",
            mode="authorized",
            outline_card="nursing_round",
        )
        self.assertEqual(result["status"], "failed")
        self.assertTrue(any("唯一视觉效果依据" in item for item in result["ai"]["errors"]))

    def test_missing_ignore_residue_instruction_fails(self) -> None:
        customer, _ = build_locked_customer(
            DRAFT,
            date="20260816",
            version="v01",
            confirmation="客户已明确确认，按这版做",
        )
        ai = build_ai_text(customer, "5张效果参考图由使用者另行提供")
        ai = ai.replace(
            "- 如果文字文件中仍残留颜色、字体、字号、版式、容器、区域比例、图形、图标或装饰说明，一律忽略。\n",
            "",
            1,
        )
        result = validate_pair(
            customer,
            ai,
            route="nursing_case",
            mode="authorized",
            outline_card="nursing_round",
        )
        self.assertEqual(result["status"], "failed")
        self.assertTrue(any("忽略残留视觉微操" in item for item in result["ai"]["errors"]))

    def test_missing_learn_reference_instruction_fails(self) -> None:
        customer, _ = build_locked_customer(
            DRAFT,
            date="20260816",
            version="v01",
            confirmation="客户已明确确认，按这版做",
        )
        ai = build_ai_text(customer, "5张效果参考图由使用者另行提供")
        ai = ai.replace(
            "- 请自行学习参考稿的视觉语言、构图方式、信息层级、页面节奏和整体质感，并据此完成设计。\n",
            "",
            1,
        )
        result = validate_pair(
            customer,
            ai,
            route="nursing_case",
            mode="authorized",
            outline_card="nursing_round",
        )
        self.assertEqual(result["status"], "failed")
        self.assertTrue(any("学习参考稿" in item for item in result["ai"]["errors"]))

    def test_visual_control_field_fails(self) -> None:
        bad = DRAFT.replace(
            "- 页面任务：说明护理风险与闭环措施",
            "- 页面任务：说明护理风险与闭环措施\n- 容器策略：结构化",
        )
        result = self.validate_draft(bad)
        self.assertTrue(any("视觉控制字段" in item for item in result["errors"]))

    def test_natural_language_visual_micromanagement_fails(self) -> None:
        instructions = (
            "- 制作要求：本页采用蓝色卡片和左右分栏布局",
            "- 本页采用蓝色卡片突出核心结论",
            "- 图标放置在标题右侧",
        )
        for instruction in instructions:
            with self.subTest(instruction=instruction):
                bad = DRAFT.replace(
                    "- 页面任务：说明护理风险与闭环措施",
                    f"- 页面任务：说明护理风险与闭环措施\n{instruction}",
                )
                result = self.validate_draft(bad)
                self.assertTrue(
                    any("视觉控制字段" in item for item in result["errors"])
                )

    def test_incomplete_table_fails(self) -> None:
        bad = DRAFT.replace(
            "- 表格：无\n- 图表数据：无\n- 来源脚注：客户去标识化病例摘要，测试资料",
            "- 表格：\n  | 项目 | 结果 |\n  |---|---|\n- 图表数据：无\n- 来源脚注：客户去标识化病例摘要，测试资料",
        )
        result = self.validate_draft(bad)
        self.assertTrue(any("完整Markdown" in item for item in result["errors"]))

    def test_complete_chart_data_passes(self) -> None:
        chart = DRAFT.replace(
            "- 图表数据：无\n- 来源脚注：客户去标识化病例摘要，测试资料",
            "- 图表数据：\n"
            "  • 数据关系：趋势\n"
            "  • 分类或时间：第1日、第2日\n"
            "  • 系列：护理项目完成率\n"
            "  • 数值：70、90\n"
            "  • 单位：百分比\n"
            "  • 样本量或统计口径：完整模拟；应完成项目为分母\n"
            "  • 数据来源：完整模拟测试数据\n"
            "- 来源脚注：客户去标识化病例摘要，测试资料",
        )
        result = self.validate_draft(chart)
        self.assertEqual(result["errors"], [])

    def test_customer_topic_may_legitimately_mention_chatgpt(self) -> None:
        topic = DRAFT.replace(
            "护理评估显示患者存在跌倒风险和吞咽风险，需要持续复评。",
            "ChatGPT仅作为本页讨论对象；护理评估内容仍需专业人员核对。",
        )
        result = self.validate_draft(topic)
        self.assertEqual(result["errors"], [])

    def test_locked_document_rejects_pending_item(self) -> None:
        pending = DRAFT.replace("- 待确认项总数：0", "- 待确认项总数：1", 1).replace(
            "- 待确认项：无\n- 不得改动：风险名称、措施与来源",
            "- 待确认项：需确认风险评分时间\n- 不得改动：风险名称、措施与来源",
        )
        locked, _ = build_locked_customer(
            pending,
            date="20260816",
            version="v01",
            confirmation="客户已明确确认",
        )
        result = validate_document(
            locked,
            stage="locked",
            role="customer",
            route="nursing_case",
            mode="authorized",
            outline_card="nursing_round",
        )
        self.assertTrue(any("仍有待确认项" in item for item in result["errors"]))

    def test_e2_unverified_draft_may_exist_but_is_blocked(self) -> None:
        draft = DRAFT.replace(
            "- 证据等级：E1 常规医学内容",
            "- 证据等级：E2 时效性或高风险医学内容",
        ).replace(
            "- 必须核验的医学主张：无",
            "- 必须核验的医学主张：护理风险处置建议",
        ).replace(
            "- 联网许可：不需要\n- 联网核验状态：不需要（仅使用客户事实，无时效性外部医学主张）\n- 证据冻结状态：可冻结",
            "- 联网许可：未允许\n- 联网核验状态：未授权-待核验\n- 证据冻结状态：阻断",
        ).replace(
            "- 未完成证据项总数：0",
            "- 未完成证据项总数：1",
        ).replace(
            "- 证据状态：客户事实\n- 待确认项：无\n- 不得改动：风险名称、措施与来源",
            "- 证据状态：待核验\n- 待确认项：无\n- 不得改动：风险名称、措施与来源",
        )
        result = self.validate_draft(draft)
        self.assertEqual(result["errors"], [])

        locked, _ = build_locked_customer(
            draft,
            date="20260820",
            version="v02",
            confirmation="客户已明确确认",
        )
        locked_result = validate_document(
            locked,
            stage="locked",
            role="customer",
            route="nursing_case",
            mode="authorized",
            outline_card="nursing_round",
        )
        self.assertEqual(locked_result["status"], "failed")
        self.assertTrue(any("待核验" in item for item in locked_result["errors"]))

    def test_e2_verified_locked_document_passes(self) -> None:
        verified = DRAFT.replace(
            "- 证据等级：E1 常规医学内容",
            "- 证据等级：E2 时效性或高风险医学内容",
        ).replace(
            "- 必须核验的医学主张：无",
            "- 必须核验的医学主张：护理风险处置建议",
        ).replace(
            "- 联网许可：不需要\n- 联网核验状态：不需要（仅使用客户事实，无时效性外部医学主张）",
            "- 联网许可：已允许\n- 联网核验状态：已联网核验（2026-08-20）",
        ).replace(
            "- 证据状态：客户事实\n- 待确认项：无\n- 不得改动：风险名称、措施与来源",
            "- 证据状态：已联网核验\n- 待确认项：无\n- 不得改动：风险名称、措施与来源",
        ).replace(
            "- 检索日期：无",
            "- 检索日期：2026-08-20",
        )
        customer, _ = build_locked_customer(
            verified,
            date="20260820",
            version="v02",
            confirmation="客户已明确确认",
        )
        result = validate_document(
            customer,
            stage="locked",
            role="customer",
            route="nursing_case",
            mode="authorized",
            outline_card="nursing_round",
        )
        self.assertEqual(result["errors"], [])

    def test_e3_locked_document_requires_claim_evidence_map(self) -> None:
        verified = DRAFT.replace(
            "- 证据等级：E1 常规医学内容",
            "- 证据等级：E3 科研或强循证内容",
        ).replace(
            "- 必须核验的医学主张：无",
            "- 必须核验的医学主张：护理风险评估与干预原则",
        ).replace(
            "- 联网许可：不需要\n- 联网核验状态：不需要（仅使用客户事实，无时效性外部医学主张）",
            "- 联网许可：已允许\n- 联网核验状态：已联网核验（2026-08-20）",
        ).replace(
            "- 检索日期：无",
            "- 检索日期：2026-08-20",
        )
        customer, _ = build_locked_customer(
            verified,
            date="20260820",
            version="v02",
            confirmation="客户已明确确认",
        )
        result = validate_document(
            customer,
            stage="locked",
            role="customer",
            route="nursing_case",
            mode="authorized",
            outline_card="nursing_round",
        )
        self.assertTrue(any("核心主张证据映射" in item for item in result["errors"]))

    def test_e3_verified_claim_evidence_map_passes(self) -> None:
        verified = DRAFT.replace(
            "- 证据等级：E1 常规医学内容",
            "- 证据等级：E3 科研或强循证内容",
        ).replace(
            "- 必须核验的医学主张：无",
            "- 必须核验的医学主张：护理风险评估与干预原则",
        ).replace(
            "- 联网许可：不需要\n- 联网核验状态：不需要（仅使用客户事实，无时效性外部医学主张）",
            "- 联网许可：已允许\n- 联网核验状态：已联网核验（2026-08-20）",
        ).replace(
            "- 检索日期：无\n- 核心主张证据映射：无",
            "- 检索日期：2026-08-20\n"
            "- 核心主张证据映射：第3页护理风险主张；直接支持来源：https://example.org/guideline；支持关系：支持持续评估原则",
        )
        customer, _ = build_locked_customer(
            verified,
            date="20260820",
            version="v02",
            confirmation="客户已明确确认",
        )
        result = validate_document(
            customer,
            stage="locked",
            role="customer",
            route="nursing_case",
            mode="authorized",
            outline_card="nursing_round",
        )
        self.assertEqual(result["errors"], [])


if __name__ == "__main__":
    unittest.main()

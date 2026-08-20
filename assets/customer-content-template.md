医学PPT逐页内容客户确认稿

【项目参数】

- 项目名称：{{project_name}}
- PPT类型：{{ppt_type}}
- 主题：{{topic}}
- 使用场景：{{setting}}
- 核心受众：{{audience}}
- 汇报目的：{{objective}}
- 页数：{{page_count}}页
- 汇报时长：{{duration}}
- 大纲来源：{{outline_source}}
- 大纲卡ID：{{outline_card_id_or_none}}
- 基础内容路由：{{route}}
- 语言：简体中文

【版本与内容状态】

- 文档用途：客户确认
- 内容状态：待确认
- 内容版本：{{version}}
- content_lock_id：待确认
- 确认记录：未确认
- 待确认项总数：{{pending_count}}
- 未完成证据项总数：{{unresolved_evidence_count}}

【输入资料与补全边界】

- 客户已提供资料：{{provided_materials}}
- 内容补全模式：{{content_mode}}
- 禁止改写内容：{{protected_content}}
- 证据等级：{{evidence_level}}
- 证据等级判定依据：{{evidence_level_rationale}}
- 必须核验的医学主张：{{claims_requiring_verification_or_none}}
- 联网许可：{{web_permission}}
- 联网核验状态：{{web_status}}
- 证据冻结状态：{{evidence_freeze_status}}
- 隐私处理：{{privacy_policy}}
- 医学审核要求：{{medical_review}}
- 参考文件用途：{{reference_role}}
- 制作参考状态：由制作方另行处理／本次无参考

【显式目录与页数分配】

{{outline_and_pages}}

目录页只显示：{{directory_visible_text}}

【内容逻辑约束（不作为目录标题）】

以下闭环只用于组织和校验内容，不得直接替代目录标题。

{{content_closure}}

【逐页完整内容】

第1页｜封面

【页面可见内容】
- 主标题：{{cover_title}}
- 副标题：{{cover_subtitle_or_none}}
- 正文：
  • {{cover_identity_line}}
- 核心结论：无
- 表格：无
- 图表数据：无
- 来源脚注：本页无外部医学主张

【内容说明（不进入PPT）】
- 所属目录章节：前置页
- 页面类型：封面
- 页面任务：识别主题与汇报身份
- 内容性质：{{cover_content_nature}}
- 证据状态：{{cover_evidence_status}}
- 待确认项：{{cover_pending_or_none}}
- 不得改动：{{cover_protected_content}}

第2页｜{{slide_2_title}}

【页面可见内容】
- 正文：
  • {{slide_2_complete_visible_copy}}
- 核心结论：{{slide_2_visible_takeaway_or_none}}
- 表格：{{slide_2_complete_table_or_none}}
- 图表数据：{{slide_2_complete_chart_data_or_none}}
- 来源脚注：{{slide_2_visible_source}}

【内容说明（不进入PPT）】
- 所属目录章节：{{slide_2_outline_section}}
- 页面类型：{{slide_2_page_type}}
- 页面任务：{{slide_2_content_task}}
- 内容性质：{{slide_2_content_nature}}
- 证据状态：{{slide_2_evidence_status}}
- 待确认项：{{slide_2_pending_or_none}}
- 不得改动：{{slide_2_protected_content}}

{{remaining_slides}}

【待确认事项汇总】

{{pending_items_or_none}}

【主要资料与医学审核】

- 客户资料：{{client_sources}}
- 指南、共识、论文或制度：{{medical_sources}}
- 检索日期：{{retrieval_date_or_none}}
- 核心主张证据映射：{{claim_evidence_map_or_none}}
- 仍待医学审核：{{medical_review_items}}
- 版本确认方式：只有明确“内容确认，可以制作”或“按这版做”后才冻结；其他反馈均视为继续修改。

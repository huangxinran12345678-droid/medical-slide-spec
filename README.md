# medical-slide-spec

面向医学与护理演示的逐页内容规格 Skill。它把客户资料整理为可直接进入PPT制作阶段的逐页完整文案，并通过证据等级、联网核验、客户确认和内容锁，控制医学主张、病例事实与视觉制作之间的边界。

## 适用场景

- 护理查房、教学查房、护理个案
- PDCA、品管圈、RCA
- 患者宣教、护理培训
- 科研开题、答辩、循证转化
- 述职竞聘和新技术项目

## 主要能力

- 自动识别演示类型并选择大纲卡
- 区分客户事实、建议补全、待确认项和模拟内容
- 输出逐页完整正文、表格、图表数据和来源脚注
- E0—E3证据分级与高风险医学主张门禁
- E2当次权威来源和时效核验
- E3核心主张与指南、DOI、PMID或官方链接映射
- 客户确认后生成客户终版与视觉AI投喂版
- 用`content_lock_id`保证两版可见内容同源
- 对患者身份信息执行去标识化要求

## 目录

```text
medical-slide-spec/
├─ SKILL.md
├─ agents/
├─ assets/
├─ references/
│  └─ outline-cards/
└─ scripts/
```

## 安装

将仓库克隆到Codex技能目录：

```powershell
git clone https://github.com/huangxinran12345678-droid/medical-slide-spec.git `
  D:\CodexWorkspace\.codex\skills\medical-slide-spec
```

如果目标目录已经存在，请先自行备份或改用新的目录；不要覆盖仍在使用的版本。

## 使用方式

在Codex中指定该Skill，并提供客户资料目录或文件：

```text
[$medical-slide-spec](.../medical-slide-spec/SKILL.md)
请把这批护理查房资料整理成逐页PPT内容。
```

Skill会先确认资料边界、演示类型、受众、页数和证据等级，再生成客户确认稿。E2与E3在冻结前需要完成当次联网核验；E3还要求核心主张逐条映射证据。

## 校验

```powershell
py -X utf8 scripts\validate_outline_library.py
py -X utf8 scripts\test_content_package.py
```

冻结后的客户终版与视觉AI版可使用：

```powershell
py -X utf8 scripts\validate_content_package.py locked "<客户终版>" `
  --ai "<视觉AI版>" `
  --route nursing_case `
  --mode authorized `
  --outline-card nursing_round
```

## 重要边界

- 结构校验通过不等于医学终审通过。
- 文献存在不等于它能够直接支持当前主张。
- 客户确认不等于本院制度、诊断或实际护理执行已被证明。
- 不得把建议补全写成客户原始事实。
- 不得上传患者姓名、住院号、身份证号、电话、精确地址、面部图像或未经授权的病历资料。
- 视觉AI只能制作已冻结内容，不承担医学判断或内容改写。

详细工作流、证据策略和内容锁规则见[SKILL.md](SKILL.md)及`references/`。

## 许可证

本项目采用[MIT许可证](LICENSE)。

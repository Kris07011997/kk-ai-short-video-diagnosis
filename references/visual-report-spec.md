# KK·AI短片诊断 PDF 规范

正式报告只有一个文件：中文为 `KK-AI短片诊断报告.pdf`，英文为 `KK-AI-Video-Diagnosis-Report.pdf`。横版 16:9，完整输出所选语言的文字，页数随内容自然变化。内部 JSON、证据图与音轨不属于交付清单。

## 报告结构

1. 作品判断：一句话判断、创作意图、置信度。
2. 值得保留：最多两项，原片截图、时间点及理由；没有足够证据时省略，不能编造优点。
3. 核心问题：零至三个，各含两至四帧原片证据、问题原因、适用方法、为什么适用、修改动作及方法来源。未发现明确问题时允许为空，但仍需在“值得保留”中提供至少一项带真实时间点的观察。
4. 第一轮修改顺序：最多五条，下一次只练一个判断，以及本次证据限制。
5. 延伸学习：逐项对应问题，说明出处、推荐理由与证据层级；没有直接来源时直说。

## 数据格式

复制 `report-plan.example.json` 到工作目录后填写真实内容。

- `language`：`zh`（简体中文）或 `en`（英文）。用户明确指定优先，否则跟随请求主要语言。旧计划缺省为 `zh`；其他值拒绝导出。自由文本须由 Agent 先按所选语言写好，渲染器只切换固定标签、元数据标签和文件名。英文示例见 `report-plan.en.example.json`。
- `source_video`：原片路径，相对路径以计划文件所在目录为基准。
- `title`、`one_line_judgment`：作品标题与判断。
- `creator_intent`：`summary` 和 `confidence`（high / medium / low）。
- `strengths`：`start`、`headline`、`evidence`。
- `issues`：`id`、`start`、`end`、`headline`、`evidence`、`action`、`confidence`、`evidence_moments`、`kk_method`。
- `evidence_moments`：2 至 4 个对象，分别写 `time`（秒）和 `label`，来自当前原片。
- `kk_method`：`name`、`rule`、`why_here`、`case_ids`；来源编号用真实检索结果，不填占位词。没有直接来源时 `case_ids` 可为空，并填写 `reference_note` 说明依据来自原片观察、尚未匹配直接案例。
- `quick_actions`：有问题时为 1 至 5 条按优先级排列的动作；无明确问题时可为空。
- `next_practice`：下次作品的一个练习目标。
- `evidence_limits`：字符串数组，无实质限制可为空。
- `further_learning`：0 至 6 项，无直接匹配来源时可为空。每项写 `issue_id`、`source_type`、`reference_level`、`focus`。匹配到来源时补 `source_id` 和 `title`。

`source_type` 使用 `daily_shot`、`long_form_tutorial` 或 `unmatched`；`reference_level` 使用 `method_level` 或 `shot_group`。PDF 按所选语言显示标签，旧版对应中文值仍可读取。镜头组级仅限已实际核对原作品的情况，另需 `user_start`、`user_end`、`user_group_label`、`source_start`、`source_end`、`source_group_label`。教学转写的时间码不能冒充原作品镜头时间。

## 完整性与视觉

- 方法原理、`why_here`、所有学习条目和证据限制都进入 PDF，不依赖其他报告补全。
- 长段落自动换行、续页；不能加省略号丢弃正文或无限缩小字体。
- 截图完整等比展示，不能裁去画面边缘的关键信息。时间标签来自已校验的截图时间。
- 指定时间点缺少准确截图时，从同一原片补取；来源不符、截图损坏或无法抽取时停止正式导出。
- 沿用清晰的浅底正文、深蓝文字与冰蓝强调，保留充分留白。
- PDF 只能显示真实证据，不能生成假“修改后”画面。
- 导出后检查每一页。程序检查的是文件结构与文字完整性，不证明诊断结论正确。

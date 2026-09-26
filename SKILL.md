---
name: kk-ai-short-video-diagnosis
description: Review edited videos using real timestamps, visuals, audio and KK methods. Deliver one PDF in Chinese or English, following the user's requested language. Supports diagnosis and revision review, not view prediction or scriptwriting from scratch. 根据用户已拍摄或剪辑的短视频，结合真实时间点、画面、声音和内置方法库诊断问题，输出一份带截图与修改建议的 PDF 报告。适用于作品诊断和修改后复查，不用于预测流量、账号定位或从零代写脚本。
---

# KK·AI短片诊断 v1

一个免费开源的完整 Skill。正式报告只有一份 PDF：中文为 `KK-AI短片诊断报告.pdf`，英文为 `KK-AI-Video-Diagnosis-Report.pdf`，完整结论、证据、修改动作与学习依据都写进这份 PDF。

## 输出语言 / Output language

- 用户明确指定的报告语言优先；未指定时，跟随当前请求的主要语言。中文请求输出中文，英文请求输出英文。混合语言时沿用对话主要语言；无法判定才简短询问。不根据视频对白、字幕、文件名或方法库语言决定报告语言。
- 支持简体中文 `zh` 和英文 `en`。用户请求其他语言时，确认采用中文或英文；不静默承诺其他语言支持。
- 在内部计划顶层写 `language: "zh"` 或 `language: "en"`。结论、意图、优点、问题、截图说明、方法解释、修改动作、学习建议、证据限制及最终回复都使用所选语言。JSON 键名、方法编号、来源编号、文件路径保持原样；原作品名称和短引用可保留原文并附译文。
- The user's explicit language choice overrides the language of their prompt. Otherwise, respond in the main language of the current request: Chinese (`zh`) or English (`en`). Write all diagnostic prose in that language before rendering. The renderer localizes labels and filenames; it does not translate prose or analyze video on its own.
- 知识库主要为中文。处理英文请求时，先把题材、症状和镜头或声音功能转为中文检索词，必要时保留英文关键词辅助检索；方法卡编号可直接检索。阅读原始依据后，用所选语言解释，不改写来源编号。英语检索无结果时，不能跳过中文检索直接判定没有依据。
- 报告元数据使用稳定代码：`source_type` 为 `daily_shot`、`long_form_tutorial` 或 `unmatched`；`reference_level` 为 `method_level` 或 `shot_group`。PDF 自动显示对应中英文标签。旧版中文字段值仍兼容。

## 先确认作品与意图

以用户原片为诊断证据。先完整看、听，再检索方法；抽帧不能代替观看运动和听取音轨。具体规则见 [视频证据](references/video-evidence.md)。

用户视频为必要材料。结合已知上下文确认：希望观众记住什么、给谁看、最不满意哪里、希望获得什么感觉。已有答案不重复追问；能从作品推断的意图注明置信度，缺少平台等补充信息不阻断诊断。需要时用 [定位卡](诊断前定位卡.md)。

无法观看原片时明确说明限制，先给有限观察，不伪造时间点或正式完成状态。涉及声音时，完整听取音轨后再读 [声音诊断框架](references/sound-diagnostic-framework.md)；不凭截图推测混音和声画同步。

## 按问题检索，避免整库加载

先读 [判断卡说明](knowledge/judgment-cards/README.md) 与 [题材地图](knowledge/case-maps/README.md)，再调用：

```bash
python scripts/resolve_case_maps.py "作品类型和问题描述"
python scripts/search_embedded_knowledge.py "具体症状 镜头或声音功能" --map vlog --limit 6 --json
```

`--map` 可选 vlog、travel、emotional、product、space、character、narrative、sound、tutorial、ai-visual。按实际作品选取；检索结果只供判断，不自动等于作品存在该问题。

- 判断卡共有 79 张；案例地图共 10 类。知识库按需读，避免把大量转写塞进上下文。
- 产品、品牌、企业宣传与商业空间题材，同时阅读 `knowledge/kk-full-library/case-atlas/11_产品广告与商业空间_完整版.md`。
- KK 编号的唯一方法溯源主索引为 `knowledge/evidence/method-card-evidence.jsonl`，保留编号与原始证据关系。
- 更多索引见 [完整知识库](knowledge/kk-full-library/README.md)。机器转写和稀疏关键帧是待核对的线索；教学讲解时间不等于原作品时间。未实际核对原作品时，引用层级只能是“方法级”。
- 案例用来解释方法，不能替代当前用户作品的证据。没有直接来源就写“暂未匹配直接案例”，不凑案例。

## 形成可执行诊断

优先判断观众能否理解、创作目标是否清楚，再看结构、镜头信息、节奏与声音，最后看装饰。保留有证据的有效表达，最多 2 项；核心问题为 0 至 3 个，必须是独立原因，不能凑数。没有明确问题时，用真实片段支持结论，不为满足格式而虚构缺点。

每个问题写清：原片发生了什么、观众为什么受影响、适用的方法及原因、先怎么重剪、确有必要时补拍什么。用 2 至 4 个真实原片时间点定位；声音问题的文字还要说明实际听到了什么。建议落到删、移、缩短、替换、补拍等动作，不承诺播放、涨粉或收益。

修改后复查时，读取旧报告并检查新作品对应片段，逐项说明已解决、部分解决、未解决或出现新问题；新旧时间轴分开记录。

## 只制作一份完整 PDF

详细数据格式和排版要求见 [报告规范](references/visual-report-spec.md)。中文示例在 [report-plan.example.json](references/report-plan.example.json)，英文示例在 [report-plan.en.example.json](references/report-plan.en.example.json)，它仅说明格式，不能当成真实诊断。

1. 在任务工作目录准备原片截图、元数据；声音诊断需要时加 `--extract-audio`。原片保持原样。

   ```bash
   python scripts/prepare_video_review.py "用户视频.mp4" --output "工作目录/evidence"
   ```

2. 将诊断写入内部 `诊断计划.json`，使用 `kk_method`，不添加配音、课件等字段。内部计划、截图和提取的音轨放在工作目录，不作为正式报告交付。

3. 使用唯一正式导出入口；它检查计划、截图来源及依赖，必要时从原片补取指定时间点的截图，然后生成 PDF。

   ```bash
   python scripts/build_pdf_report.py "工作目录/诊断计划.json" --evidence-dir "工作目录/evidence" --output-dir "交付目录"
   ```

4. 渲染并查看最终 PDF 的每一页，检查所选语言的文字、英文单词换行、完整画面、时间标签、长文续页、图片和页脚。机器校验不能替代视觉检查。正文不得静默截断；内容较长时自动续页。

5. 交付 PDF 及所在文件夹链接，简述最优先的修改和实际证据限制。不额外交付 PPT、MP3 或诊断计划。导出失败时明确说明未完成，不把文字草稿称作 PDF 报告。

## 环境与维护

环境说明、安装与调用示例见 [README](README.md)。PDF 生成不需要在线语音服务。视频抽帧需要 FFmpeg 和 ffprobe；已有合格证据时的 PDF 渲染依赖以环境检查结果为准。

修改知识库后运行 `python scripts/validate_method_card_evidence.py`，确认方法来源仍可追溯。原创内容的使用见 [开源说明](开源与使用说明.md)，第三方材料范围见 [第三方说明](THIRD_PARTY_NOTICES.md)。

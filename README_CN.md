# KK·AI短片诊断 v1

[English](README.md) | **简体中文**

**免费开源 · 一个完整 Skill · 一份 PDF 报告**

让 AI 结合你的真实作品，回答三个问题：哪里影响了观看，为什么，先怎么改。

适用于已经拍摄或剪辑的 Vlog、旅拍、产品片、人物片、剧情短片、教程口播和 AI 短片。它会结合原片时间点、截图和实际声音分析，保留有效表达，给出可执行的修改动作。报告只输出 PDF。

## 中文与英文报告

用户明确指定的语言优先；未指定时，中文请求输出中文，英文请求输出英文。视频对白或资料库的语言不会替代你的选择。

> 请诊断这个视频，用英文输出 PDF 报告。

> Review this video and deliver the PDF report in Chinese.

标题、分析、截图说明、修改建议、方法解释和页脚均跟随所选语言。方法库保留中文，Agent 用中文关键词检索，再用所选语言解释；来源编号保持不变。

中文报告：`KK-AI短片诊断报告.pdf`。英文报告：`KK-AI-Video-Diagnosis-Report.pdf`。每次只交付所选语言的一份 PDF。

## 快速开始

1. 下载仓库，把完整的 `kk-ai-short-video-diagnosis` 目录放入所用 Agent 的技能目录，或让 Agent 读取本目录的 `SKILL.md`。不要只复制一个 Markdown 文件。
2. 使用 Python 3.10 或以上版本，安装依赖：

   ```bash
   python -m pip install -r requirements.txt
   python scripts/check_environment.py --output-dir "你的工作目录" --json
   ```

3. 视频抽帧需要 FFmpeg 与 ffprobe 在 PATH 中。在能读取视频并执行本地脚本的 Agent 中，上传原片并输入：

   > 使用 $kk-ai-short-video-diagnosis 分析这个视频。我希望观众记住……，最不满意的是……。请用真实时间点和截图说明原因，给出修改建议，只交付 PDF 报告。

Codex 常用技能目录为 `$CODEX_HOME/skills` 或 `~/.codex/skills`。其他工具按各自的技能加载方式使用。是否能完整看听视频、执行 Python 和导出 PDF，以当前运行环境的实际能力为准。

## 报告包含什么

- 作品目标与一句话判断。
- 值得保留的片段及原片证据。
- 最多三个独立问题：具体时间点、截图、原因、修改动作及方法依据。
- 第一轮修改顺序、下一次练习目标与本次证据限制。
- 有直接匹配来源时提供延伸学习。

没有明确问题就如实说明，不强行凑数。没有直接案例就标明依据限制，不编造引用。长文会自动续页；截图保持原比例，不能裁掉关键信息。

## 工作方式

先完整看听作品，再按问题检索方法卡与案例地图，最后形成内部诊断计划并生成 PDF。检索不会把不相关案例作为空结果的填充；同一证据跨索引出现时会去重。

抽帧、内部 JSON 和临时文件放在任务工作目录，正式交付目录只放 PDF。声音分析使用原片音轨，不需要在线语音合成服务。工具不会上传用户作品；你所使用的 Agent 平台如何处理输入，由该平台设置决定。

详细字段见 [报告规范](references/visual-report-spec.md)，输入模板见 [示例计划](references/report-plan.example.json)。该模板只演示格式，运行前必须替换为真实作品与观察。

## 开源与贡献

版本：`1.0.0`。KK 原创代码、流程与方法整理采用 [MIT License](LICENSE)，可免费使用、修改和分享。字体和第三方来源的具体范围见 [第三方说明](THIRD_PARTY_NOTICES.md)。

欢迎提交问题、修复和实际使用反馈。反馈诊断问题时，提供有权分享的最小视频片段、复现步骤及预期结果；不要把私人原片或账号凭据直接提交到公开仓库。

```bash
python -m unittest discover -s tests -v
python scripts/validate_method_card_evidence.py
```

自动测试检查检索、数据校验和导出行为，不能替代对真实作品诊断质量的判断。

完整性校验：运行 `python scripts/verify_package.py`，逐文件检查大小和 SHA-256。主动修改文件后，运行 `python scripts/verify_package.py --write` 更新清单。

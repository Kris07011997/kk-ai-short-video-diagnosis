# KK AI Video Diagnosis v1

**English** | [简体中文](README_CN.md)

**One complete Skill. One actionable PDF report. In Chinese or English.**

KK turns six years of video review experience, including work on content with over 100 million views, into a workflow for reviewing your own edits.

Many AI tools help you make a video. This Skill helps you examine the result: where the viewing experience breaks down, why it happens, and what to change first.

It reviews edited vlogs, travel videos, product and brand videos, portraits, narrative shorts, tutorials and AI shorts. Each diagnosis connects the actual footage, timestamps and audio observations to practical editing decisions.

## Choose your report language

An explicit language request takes priority. Otherwise, the Agent follows the main language of your request: Chinese or English. The language spoken in the video does not determine the report language.

> Review this video and deliver the PDF report in English.

> 请诊断这条视频，用英文输出 PDF 报告。

> Review this video and write the PDF report in Chinese.

The diagnosis, captions, method explanations, suggested edits, section labels and footer use the selected language. Source IDs and original work titles retain their identity. The knowledge base remains primarily Chinese; the Agent searches it with Chinese keywords and explains relevant findings in the selected language.

One PDF is delivered per review:

- Chinese: `KK-AI短片诊断报告.pdf`
- English: `KK-AI-Video-Diagnosis-Report.pdf`

The Agent writes the diagnostic prose in the selected language before export. The PDF renderer localizes fixed labels and metadata; it does not translate prose or analyze footage by itself.

## Methods and cases

The v1 package contains **79 review method cards, 94 deduplicated case breakdowns and 10 topic maps**. The maps cover vlogs, travel, emotional storytelling, products, spaces, characters, narratives, sound, tutorials and AI visuals.

The workflow starts with the goal of the specific video, then retrieves relevant methods and cases. It does not impose the same editing pattern on every genre. Third-party materials have separate distribution terms; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Quick start

1. Place the complete `kk-ai-short-video-diagnosis` folder in your Agent's skills directory, or ask the Agent to read `SKILL.md` in this folder. Keep the scripts, references, fonts and knowledge folders together.
2. Use Python 3.10 or newer and install the dependencies:

   ```bash
   python -m pip install -r requirements.txt
   python scripts/check_environment.py --output-dir "your-work-directory" --json
   ```

3. Make FFmpeg and ffprobe available on PATH for frame extraction. Provide the source video to an Agent that can inspect video and audio and execute local scripts:

   ```text
   Use kk-ai-short-video-diagnosis to review this video.
   My intended audience is ...
   I want viewers to remember ...
   I would most like to improve ...
   Explain the problems using actual timestamps and screenshots.
   Keep what works and prioritize actionable edits.
   Deliver one PDF report in English.
   ```

For Codex, common skill locations are `$CODEX_HOME/skills` or `~/.codex/skills`. Other Agents use their own skill loading mechanisms. Full audiovisual review depends on the capabilities available in the chosen environment.

## What the report contains

- Creative intent and an overall judgment.
- Up to two strengths, supported by source footage.
- Zero to three distinct issues, with timestamps, screenshots, explanations and concrete edits.
- Relevant KK methods and traceable references.
- A prioritized revision list and one focus for the next video.
- Further learning and any material evidence limitations.

The workflow permits a review with no clear issue. It does not invent problems or references to fill a template. Long text continues onto additional pages, and screenshots keep their original aspect ratio.

For a revision review, supply the new video and the previous report. The Agent checks which issues are resolved, partly resolved or still present, and whether new issues appeared.

## How it works

The Agent reviews the full video and audio, identifies concrete symptoms, retrieves relevant method cards and cases, and writes an internal report plan. The export script verifies the plan and the source of its screenshots before generating the PDF.

Intermediate JSON, extracted frames and audio stay in the work directory. The final delivery contains only the PDF. No online speech synthesis service is required. The bundled scripts do not upload the video; input handling by your Agent provider follows that provider's settings.

Plan examples: [Chinese](references/report-plan.example.json) / [English](references/report-plan.en.example.json). These are format templates, not completed diagnoses. Replace all placeholders with observations from the actual video. Detailed field rules are in the [report specification](references/visual-report-spec.md).

## Development and license

Version: `1.0.0`. KK's original code, workflow and method organization are available under the [MIT License](LICENSE). Font and third-party source terms are listed separately in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python scripts/validate_method_card_evidence.py
python scripts/verify_package.py
```

Tests cover retrieval, validation, language compatibility and PDF text preservation. They do not substitute for assessing the quality of a real video diagnosis.

Feedback and contributions are welcome. When reporting a problem, share a minimal example you have permission to distribute, reproduction steps and the expected result.

**KK / In the AI era, keep learning. Keep improving.**

Package integrity: `PACKAGE-MANIFEST.json` records every distributed file and its SHA-256. After intentional changes, refresh it with `python scripts/verify_package.py --write`.

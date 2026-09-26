#!/usr/bin/env python3
"""Validate a KK visual-report plan before rendering."""

from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path
from report_language import language_of, canonical_code, SOURCE_TYPES, REFERENCE_LEVELS


CONFIDENCE = {"high", "medium", "low"}


def fail(messages: list[str]) -> None:
    for message in messages:
        print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(2)


def resolve_path(value: str, base: Path) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else (base / path).resolve()


def media_duration(path: Path) -> float | None:
    ffprobe = shutil.which("ffprobe")
    if ffprobe:
        result = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        try:
            return float(result.stdout.strip())
        except ValueError:
            pass
    mdls = shutil.which("mdls")
    if mdls:
        result = subprocess.run(
            [mdls, "-raw", "-name", "kMDItemDurationSeconds", str(path)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        try:
            return float(result.stdout.strip())
        except ValueError:
            pass
    return None


def validate(plan_path: Path) -> dict:
    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail([f"Plan not found: {plan_path}"])
    except json.JSONDecodeError as exc:
        fail([f"Invalid JSON at line {exc.lineno}: {exc.msg}"])

    if not isinstance(plan, dict):
        fail(["Plan must be a JSON object."])
    errors: list[str] = []
    try:
        language_of(plan)
    except ValueError as exc:
        errors.append(str(exc))
    base = plan_path.parent
    source_value = plan.get("source_video")
    source_duration: float | None = None
    if not isinstance(source_value, str) or not source_value.strip():
        errors.append("source_video must be a non-empty path.")
    else:
        source = resolve_path(source_value, base)
        if not source.is_file():
            errors.append(f"Source video not found: {source}")
        else:
            source_duration = media_duration(source)

    intent = plan.get("creator_intent")
    if not isinstance(intent, dict):
        errors.append("creator_intent must be an object.")
    else:
        if not str(intent.get("summary", "")).strip():
            errors.append("creator_intent.summary is required.")
        if intent.get("confidence") not in CONFIDENCE:
            errors.append("creator_intent.confidence must be high, medium, or low.")

    strengths = plan.get("strengths", [])
    if not isinstance(strengths, list) or len(strengths) > 2:
        errors.append("strengths must be a list with no more than two items.")
    elif strengths:
        for index, strength in enumerate(strengths, start=1):
            prefix = f"strengths[{index}]"
            if not isinstance(strength, dict):
                errors.append(f"{prefix} must be an object with start, headline and evidence.")
                continue
            if not str(strength.get("headline", "")).strip():
                errors.append(f"{prefix}.headline is required.")
            if not str(strength.get("evidence", "")).strip():
                errors.append(f"{prefix}.evidence is required.")
            try:
                start = float(strength.get("start"))
                if not math.isfinite(start) or start < 0:
                    raise ValueError
                if source_duration is not None and start > source_duration + 0.05:
                    errors.append(f"{prefix}.start ({start:.3f}s) exceeds source duration ({source_duration:.3f}s).")
            except (TypeError, ValueError):
                errors.append(f"{prefix}.start must be a non-negative finite number.")

    issues = plan.get("issues")
    if not isinstance(issues, list) or not 0 <= len(issues) <= 3:
        errors.append("issues must contain zero to three items.")
        issues = []
    if not issues and not strengths:
        errors.append("A report without issues still needs at least one evidence-backed observation in strengths.")

    seen_ids: set[str] = set()
    seen_headlines: set[str] = set()
    for index, issue in enumerate(issues, start=1):
        prefix = f"issues[{index}]"
        if not isinstance(issue, dict):
            errors.append(f"{prefix} must be an object.")
            continue
        issue_id = str(issue.get("id", "")).strip()
        headline = str(issue.get("headline", "")).strip()
        if not issue_id:
            errors.append(f"{prefix}.id is required.")
        elif issue_id in seen_ids:
            errors.append(f"Duplicate issue id: {issue_id}")
        seen_ids.add(issue_id)
        if not headline:
            errors.append(f"{prefix}.headline is required.")
        elif headline in seen_headlines:
            errors.append(f"Duplicate issue headline: {headline}")
        seen_headlines.add(headline)
        for field in ("evidence", "action"):
            if not str(issue.get(field, "")).strip():
                errors.append(f"{prefix}.{field} is required.")
        method = issue.get("kk_method")
        if not isinstance(method, dict):
            errors.append(f"{prefix}.kk_method must be an object.")
        else:
            for field in ("name", "rule", "why_here"):
                if not str(method.get(field, "")).strip():
                    errors.append(f"{prefix}.kk_method.{field} is required.")
            case_ids = method.get("case_ids")
            if not isinstance(case_ids, list) or not all(isinstance(case_id, str) and case_id.strip() for case_id in case_ids):
                errors.append(f"{prefix}.kk_method.case_ids must be a list of source identifiers.")
            elif not case_ids and not str(method.get("reference_note", "")).strip():
                errors.append(f"{prefix}.kk_method.reference_note is required when no direct source was matched.")
        if issue.get("confidence") not in CONFIDENCE:
            errors.append(f"{prefix}.confidence must be high, medium, or low.")
        try:
            start = float(issue.get("start"))
            end = float(issue.get("end"))
            if not math.isfinite(start) or not math.isfinite(end):
                raise ValueError
            if start < 0 or end <= start:
                errors.append(f"{prefix} must satisfy 0 <= start < end.")
            if source_duration is not None and end > source_duration + 0.05:
                errors.append(
                    f"{prefix}.end ({end:.3f}s) exceeds source duration ({source_duration:.3f}s)."
                )
        except (TypeError, ValueError):
            errors.append(f"{prefix}.start and end must be finite numbers.")

        moments = issue.get("evidence_moments")
        if not isinstance(moments, list) or not 2 <= len(moments) <= 4:
            errors.append(f"{prefix}.evidence_moments must contain two to four visual evidence points.")
        else:
            for moment_index, moment in enumerate(moments, start=1):
                moment_prefix = f"{prefix}.evidence_moments[{moment_index}]"
                if not isinstance(moment, dict):
                    errors.append(f"{moment_prefix} must be an object.")
                    continue
                if not str(moment.get("label", "")).strip():
                    errors.append(f"{moment_prefix}.label is required.")
                try:
                    time_value = float(moment.get("time"))
                    if not math.isfinite(time_value) or time_value < 0:
                        raise ValueError
                    if source_duration is not None and time_value > source_duration + 0.05:
                        errors.append(
                            f"{moment_prefix}.time ({time_value:.3f}s) exceeds source duration ({source_duration:.3f}s)."
                        )
                except (TypeError, ValueError):
                    errors.append(f"{moment_prefix}.time must be a non-negative finite number.")

    quick_actions = plan.get("quick_actions", [])
    minimum_actions = 1 if issues else 0
    if not isinstance(quick_actions, list) or not minimum_actions <= len(quick_actions) <= 5 or not all(isinstance(item, str) and item.strip() for item in quick_actions):
        errors.append(f"quick_actions must contain {minimum_actions} to five non-empty strings.")

    limits = plan.get("evidence_limits", [])
    if not isinstance(limits, list) or not all(isinstance(item, str) for item in limits):
        errors.append("evidence_limits must be a list of strings.")

    further_learning = plan.get("further_learning")
    allowed_source_types = SOURCE_TYPES
    if not isinstance(further_learning, list) or not 0 <= len(further_learning) <= 6:
        errors.append("further_learning must contain zero to six learning references.")
    else:
        issue_ids = {str(issue.get("id", "")).strip() for issue in issues if isinstance(issue, dict)}
        reference_levels = REFERENCE_LEVELS
        for index, item in enumerate(further_learning, start=1):
            prefix = f"further_learning[{index}]"
            if not isinstance(item, dict):
                errors.append(f"{prefix} must be an object.")
                continue
            if str(item.get("issue_id", "")).strip() not in issue_ids:
                errors.append(f"{prefix}.issue_id must reference an existing issue.")
            source_type = canonical_code(str(item.get("source_type", "")).strip())
            if source_type not in allowed_source_types:
                errors.append(f"{prefix}.source_type must be daily_shot, long_form_tutorial or unmatched (legacy Chinese values accepted).")
            if not str(item.get("focus", "")).strip():
                errors.append(f"{prefix}.focus is required.")
            reference_level = canonical_code(str(item.get("reference_level", "method_level")).strip())
            if reference_level not in reference_levels:
                errors.append(f"{prefix}.reference_level must be shot_group or method_level (legacy Chinese values accepted).")
            if source_type != "unmatched":
                for field in ("source_id", "title"):
                    if not str(item.get(field, "")).strip():
                        errors.append(f"{prefix}.{field} is required for a matched learning source.")
            if reference_level == "shot_group":
                for field in ("user_group_label", "source_group_label"):
                    if not str(item.get(field, "")).strip():
                        errors.append(f"{prefix}.{field} is required for a shot-group reference.")
                for start_field, end_field in (("user_start", "user_end"), ("source_start", "source_end")):
                    try:
                        start = float(item.get(start_field))
                        end = float(item.get(end_field))
                        if not math.isfinite(start) or not math.isfinite(end) or start < 0 or end <= start:
                            raise ValueError
                    except (TypeError, ValueError):
                        errors.append(f"{prefix}.{start_field} and {end_field} must satisfy 0 <= start < end for a shot-group reference.")

    if errors:
        fail(errors)
    return plan


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a visual diagnosis report plan.")
    parser.add_argument("plan", help="Path to the report-plan JSON file")
    args = parser.parse_args()
    plan_path = Path(args.plan).expanduser().resolve()
    plan = validate(plan_path)
    print("VISUAL REPORT PLAN: VALID")
    print(f"Issues: {len(plan['issues'])}")
    print(f"Quick actions: {len(plan.get('quick_actions', []))}")


if __name__ == "__main__":
    main()

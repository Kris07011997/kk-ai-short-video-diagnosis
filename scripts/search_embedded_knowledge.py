#!/usr/bin/env python3
"""Search only embedded cards, maps and portable evidence records.

Searches this skill directory only. Extra material is used only when supplied
by the user for the current task.
"""

from __future__ import annotations

import argparse
import json
import hashlib
import re
from pathlib import Path


SYNONYMS = {
    # “流水账”是跨题材症状；不预设成旅拍或 Vlog，避免检索时误把题材带偏。
    "流水账": ["事件", "段落", "推进"],
    "开头平": ["开头", "顶点", "问题", "人物入场"],
    "看不懂": ["信息", "关键动作", "镜头顺序", "结果"],
    "拖沓": ["快切", "跳切", "节奏", "无效时间"],
    "旅拍": ["旅拍", "故事", "当地", "抵达", "收尾"],
    "产品": ["产品", "使用场景", "功能", "动作", "结果"],
    "民宿": ["空间", "民宿", "关键词", "氛围", "层次"],
    "空间": ["空间", "民宿", "前中后景", "关键词"],
    "表情": ["人物", "反应", "近景", "情绪"],
    "声音": ["拟声", "氛围", "节奏", "音乐"],
    "音效": ["拟声", "氛围", "节奏", "Whoosh", "重击"],
    "whoosh": ["Whoosh", "转场", "动势", "速度"],
    "音乐": ["音乐", "切断", "环境声", "节奏"],
    "提示词": ["提示词", "信息取舍", "景别", "机位", "运动", "时长", "剪辑"],
}

# The map is chosen before retrieval.  It prevents a shared symptom such as
# “流水账” from making a travel card outrank a Vlog card in a Vlog diagnosis.
MAP_CATEGORIES = {
    "vlog": "生活Vlog",
    "travel": "旅拍",
    "emotional": "人物与情绪",
    "product": "产品片",
    "space": "空间与民宿",
    "character": "人物与情绪",
    "narrative": "叙事与剧情",
    "sound": "声音设计",
    "tutorial": "镜头与剪辑",
    # AI 镜头语言的主要依据是提示词/镜头规则本身；不按自动题材标签过滤案例。
    "ai-visual": None,
}

# The new teaching-video and spreadsheet evidence uses teaching tags rather
# than the older case-index category labels.  Route it deliberately instead of
# returning all 2,014 records for every diagnosis.
MAP_EVIDENCE_TAGS = {
    "vlog": {"Vlog", "开场结构", "镜头语言", "人物表达"},
    "travel": {"旅拍", "开场结构", "镜头语言", "剪辑节奏", "声音设计"},
    "emotional": {"人物表达", "镜头语言", "声音设计"},
    "product": {"产品与空间", "镜头语言", "剪辑节奏", "声音设计"},
    "space": {"产品与空间", "镜头语言", "声音设计"},
    "character": {"人物表达", "镜头语言", "开场结构"},
    "narrative": {"开场结构", "人物表达", "剪辑节奏"},
    "sound": {"声音设计", "剪辑节奏"},
    "tutorial": {"开场结构", "镜头语言", "剪辑节奏"},
    "ai-visual": {"镜头语言", "剪辑节奏", "声音设计"},
}


def terms(query: str) -> set[str]:
    query = query.strip().lower()
    if not query:
        raise ValueError("Query must not be empty.")
    found = {term for term in re.split(r"[\s,，、;；]+", query) if term}
    found.add(query)
    for key, additions in SYNONYMS.items():
        if key.lower() in query:
            found.add(key.lower())
            found.update(term.lower() for term in additions)
    return found


def read_jsonl(path: Path):
    with path.open(encoding="utf-8-sig") as handle:
        for number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            item = json.loads(line)
            if not isinstance(item, dict):
                raise ValueError(f"{path.name}:{number} must contain an object.")
            yield item


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from strings(child)


def score_record(record, query_terms):
    blob = " ".join(strings(record)).lower()
    matched = sorted(term for term in query_terms if term in blob)
    if not matched:
        return 0, []
    title = str(record.get("title", record.get("case_id", ""))).lower()
    return len(matched) + sum(5 for term in matched if term in title), matched


def teaching_record_matches_map(record, map_id):
    if not map_id:
        return True
    tags = set(record.get("tags", []))
    if tags:
        return bool(tags.intersection(MAP_EVIDENCE_TAGS.get(map_id, set())))
    keywords = {
        "vlog": ("vlog", "日常", "生活记录"), "travel": ("旅拍", "旅行", "城市", "露营", "骑行"),
        "emotional": ("情绪", "温情", "人物"), "product": ("产品", "企业", "工厂", "广告"),
        "space": ("民宿", "酒店", "空间", "餐厅"), "character": ("人物", "毕业", "教师", "故事"),
        "narrative": ("剧情", "故事", "悬疑", "tvc"), "sound": ("音效", "声音", "音乐", "whoosh"),
        "tutorial": ("教程", "口播", "讲解", "教学"), "ai-visual": ("镜头", "构图", "转场", "分镜"),
    }
    blob = " ".join(strings(record)).lower()
    return any(term in blob for term in keywords.get(map_id, ()))


def fingerprint(record):
    if "row" in record:
        keys = ("case_id", "source_file", "sheet", "row", "text")
    elif "card_id" in record:
        keys = ("card_id",)
    elif "text" in record:
        keys = ("source_id", "text")
    else:
        keys = tuple(sorted(record))
    normalized = {key: record.get(key) for key in keys}
    return hashlib.sha256(json.dumps(normalized, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def datasets(root):
    yield root / "judgment-cards/cards.jsonl", "judgment_card", "方法判断"
    yield root / "judgment-cards/video-teaching-cards.jsonl", "judgment_card", "方法判断"
    yield root / "evidence/method-card-evidence.jsonl", "method_card_evidence", "方法溯源证据"
    yield root / "evidence/cases.jsonl", "case_evidence", "案例文字依据"
    for name in ("teaching-source-evidence", "teaching-table-evidence", "teaching-script-evidence"):
        yield root / f"evidence/{name}.jsonl", "teaching_evidence", "教学文字依据"
    library = root / "kk-full-library"
    yield library / "kk-case-evidence-deduped.jsonl", "full_case_evidence", "案例表依据"
    yield library / "kk-all-teaching-evidence.jsonl", "full_teaching_evidence", "教学文字依据"
    yield library / "video-teaching-evidence/kk-video-teaching-evidence.jsonl", "video_teaching_lead", "机器转写线索，需交叉核对"


def search(query, root, map_id=None, kind="all", limit=6):
    query_terms = terms(query)
    maps = json.loads((root / "case-maps/index.json").read_text(encoding="utf-8"))
    if map_id and map_id not in maps:
        raise ValueError("Unknown map: " + map_id)
    # Exact identifiers resolve their source even when a caller picked a
    # different genre. They do not perform fuzzy matches against other IDs.
    exact = bool(re.fullmatch(r"(?:KK|KKT|JC|VTC)-[A-Z0-9]+|daily-mirror-[\w-]+", query.strip(), re.I))
    allowed = set(maps[map_id]["cards"]) if map_id else None
    results, seen = [], set()
    for path, record_kind, tier in datasets(root):
        if (kind == "cards" and record_kind != "judgment_card") or (kind == "cases" and record_kind == "judgment_card"):
            continue
        if not path.is_file():
            continue
        for item in read_jsonl(path):
            if exact:
                ids = [str(item.get(key, "")).lower() for key in ("card_id", "case_id", "source_id", "record_id")]
                if query.strip().lower() not in ids:
                    continue
                score, matched = 100, [query.strip().lower()]
            else:
                score, matched = score_record(item, query_terms)
                if not matched:
                    continue
                if record_kind == "judgment_card":
                    card_id = item.get("card_id", "")
                    if allowed is not None and card_id.startswith("JC-") and card_id not in allowed:
                        continue
                    if allowed is not None and card_id in allowed:
                        score += 2
                elif record_kind == "case_evidence":
                    category = MAP_CATEGORIES.get(map_id)
                    if category and category not in item.get("categories", []):
                        continue
                elif not teaching_record_matches_map(item, map_id):
                    continue
            key = fingerprint(item)
            if key in seen:
                continue
            seen.add(key)
            results.append({"kind": record_kind, "score": score, "matched_terms": matched,
                            "evidence_tier": tier, "record": item})
    results.sort(key=lambda item: (-item["score"], item["kind"], str(item["record"].get("case_id", item["record"].get("card_id", "")))))
    return results[:max(1, min(limit, 20))]


def main():
    parser = argparse.ArgumentParser(description="Search KK's embedded method cards and evidence.")
    parser.add_argument("query")
    parser.add_argument("--type", choices=["all", "cards", "cases"], default="all")
    parser.add_argument("--map", dest="map_id")
    parser.add_argument("--limit", type=int, default=6)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        results = search(args.query, Path(__file__).resolve().parent.parent / "knowledge", args.map_id, args.type, args.limit)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    elif not results:
        print("没有匹配结果。请调整症状或题材，不使用无关案例补位。")
    else:
        for item in results:
            record = item["record"]
            label = record.get("title", record.get("case_id", record.get("card_id", "未命名")))
            print(f"[{item['kind']}] {label} | score={item['score']}")


if __name__ == "__main__":
    main()

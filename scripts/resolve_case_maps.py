#!/usr/bin/env python3
"""Return mandatory v1 case maps from a user's type or problem description."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROUTES = {
    "vlog": ["vlog", "日常", "通勤", "生活"],
    "travel": ["旅拍", "旅行", "景点", "城市", "当地"],
    "emotional": ["情绪", "氛围", "感受", "治愈"],
    "product": ["产品", "功能", "品牌", "带货", "数码", "卖点"],
    "space": ["民宿", "酒店", "空间", "房间", "餐厅"],
    "character": ["人物", "表情", "反应", "关系"],
    "narrative": ["故事", "剧情", "目标", "转折", "悬念"],
    "sound": ["声音", "音效", "音乐", "whoosh", "拟声", "环境声", "重击"],
    "tutorial": ["教程", "口播", "教学", "操作", "步骤"],
    "ai-visual": ["ai视频", "ai 镜头", "提示词", "图生视频", "ai转场", "生成镜头"],
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("query")
    args = parser.parse_args()
    query = args.query.lower()
    maps = json.loads((Path(__file__).resolve().parent.parent / "knowledge" / "case-maps" / "index.json").read_text(encoding="utf-8"))
    selected = [key for key, words in ROUTES.items() if any(word in query for word in words)]
    # A symptom such as a weak opening does not establish the video's genre.
    # No match means the caller should inspect the work or search without a map.
    output = [{"map": key, "title": maps[key]["title"], "must_read_cards": maps[key]["cards"], "triggered_by": [word for word in ROUTES[key] if word in query]} for key in selected]
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
